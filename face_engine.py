"""
face_engine.py - Thread-safe, offline face detection and recognition engine
using OpenCV YuNet (FaceDetectorYN) and SFace (FaceRecognizerSF).
"""

import os
import sys
import time
import math
import cv2
import numpy as np
import threading
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Callable, Dict, Any, Tuple


# ponytail: simple resource path lookup supporting PyInstaller bundle sys._MEIPASS
def get_resource_path(relative_path: str) -> str:
    """
    Get absolute path to resource, works for development and PyInstaller bundle.
    
    Args:
        relative_path: Relative file path (e.g. 'models/face_detection_yunet_2023mar.onnx').
        
    Returns:
        Absolute path to the resource file.
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    full_path = os.path.join(base_path, relative_path)
    if not os.path.exists(full_path):
        cwd_path = os.path.abspath(relative_path)
        if os.path.exists(cwd_path):
            return cwd_path
    return os.path.abspath(full_path)


class EngineState(Enum):
    """Engine worker thread state machine."""
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    TERMINATED = "TERMINATED"
    COMPLETED = "COMPLETED"


@dataclass
class TargetFaceResult:
    """Result container for target face extraction."""
    success: bool
    crop: Optional[np.ndarray] = None
    feature: Optional[np.ndarray] = None
    bbox: Optional[Tuple[int, int, int, int]] = None
    score: float = 0.0
    message: str = ""


@dataclass
class VideoInfo:
    """Metadata container for video files."""
    video_path: str
    fps: float
    total_frames: int
    width: int
    height: int
    duration: float


@dataclass
class MatchResult:
    """Information payload generated when a target match is detected."""
    frame_index: int
    timestamp: float
    timestamp_str: str
    similarity: float
    bbox: Tuple[int, int, int, int]
    face_crop: np.ndarray
    score: float


@dataclass
class FrameStats:
    """Real-time processing statistics for UI/progress updates."""
    frame_index: int
    total_frames: int
    processed_frames: int
    fps: float
    elapsed_time: float
    eta: float
    progress_percent: float
    detected_faces_count: int
    matches_count: int


class FaceEngine:
    """
    Thread-safe face detection & recognition processing engine.
    
    Uses OpenCV YuNet ONNX model for face detection and OpenCV SFace ONNX
    model for face alignment and 128D feature extraction & cosine similarity matching.
    """

    def __init__(
        self,
        detection_model_path: Optional[str] = None,
        recognition_model_path: Optional[str] = None,
        score_threshold: float = 0.6,
        nms_threshold: float = 0.3,
        cosine_threshold: float = 0.363,  # ~0.363 default for >=80% accuracy with SFace
        top_k: int = 5000,
        backend_id: int = cv2.dnn.DNN_BACKEND_OPENCV,
        target_id: int = cv2.dnn.DNN_TARGET_CPU
    ):
        # Resolve ONNX model paths
        if detection_model_path is None:
            detection_model_path = get_resource_path("models/face_detection_yunet_2023mar.onnx")
        else:
            detection_model_path = get_resource_path(detection_model_path)

        if recognition_model_path is None:
            recognition_model_path = get_resource_path("models/face_recognition_sface_2021dec.onnx")
        else:
            recognition_model_path = get_resource_path(recognition_model_path)

        if not os.path.exists(detection_model_path):
            raise FileNotFoundError(f"YuNet detection model not found at {detection_model_path}")
        if not os.path.exists(recognition_model_path):
            raise FileNotFoundError(f"SFace recognition model not found at {recognition_model_path}")

        self.score_threshold = score_threshold
        self.nms_threshold = nms_threshold
        self.cosine_threshold = cosine_threshold
        self.top_k = top_k
        self.backend_id = backend_id
        self.target_id = target_id

        # Instantiate YuNet detector with initial dummy resolution (updated per frame/image)
        self.detector = cv2.FaceDetectorYN.create(
            model=detection_model_path,
            config="",
            input_size=(320, 320),
            score_threshold=self.score_threshold,
            nms_threshold=self.nms_threshold,
            top_k=self.top_k,
            backend_id=self.backend_id,
            target_id=self.target_id
        )

        # Instantiate SFace recognizer
        self.recognizer = cv2.FaceRecognizerSF.create(
            model=recognition_model_path,
            config="",
            backend_id=self.backend_id,
            target_id=self.target_id
        )

        # Thread management & state machine
        self._lock = threading.Lock()
        self._pause_event = threading.Event()
        self._pause_event.set()  # Set = unpaused, Clear = paused
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None
        self._state: EngineState = EngineState.IDLE

        # Target face & video metadata
        self.target_feature: Optional[np.ndarray] = None
        self.target_crop: Optional[np.ndarray] = None
        self.video_info: Optional[VideoInfo] = None

        # Callback functions for UI thread integration
        self.on_frame_update: Optional[Callable[[np.ndarray, FrameStats], None]] = None
        self.on_match_found: Optional[Callable[[MatchResult], None]] = None
        self.on_status_change: Optional[Callable[[EngineState], None]] = None
        self.on_complete: Optional[Callable[[Dict[str, Any]], None]] = None

    @property
    def state(self) -> EngineState:
        """Get current engine state in a thread-safe manner."""
        with self._lock:
            return self._state

    def _set_state(self, new_state: EngineState) -> None:
        """Update engine state and notify status change callback."""
        with self._lock:
            if self._state == new_state:
                return
            self._state = new_state

        if self.on_status_change:
            try:
                self.on_status_change(new_state)
            except Exception:
                # ponytail: ignore UI callback errors to preserve worker stability
                pass

    def set_thresholds(
        self,
        score_threshold: Optional[float] = None,
        nms_threshold: Optional[float] = None,
        cosine_threshold: Optional[float] = None
    ) -> None:
        """Dynamically update threshold values (slider configurable)."""
        with self._lock:
            if score_threshold is not None:
                self.score_threshold = score_threshold
                self.detector.setScoreThreshold(score_threshold)
            if nms_threshold is not None:
                self.nms_threshold = nms_threshold
                self.detector.setNMSThreshold(nms_threshold)
            if cosine_threshold is not None:
                self.cosine_threshold = cosine_threshold

    def load_target_image(self, image_source: Any) -> TargetFaceResult:
        """
        Load target image, detect face, align, and extract 128D feature vector.

        Args:
            image_source: File path (str) or loaded BGR image (np.ndarray).

        Returns:
            TargetFaceResult with success status, cropped/aligned face, feature vector, and bbox.
        """
        if isinstance(image_source, str):
            if not os.path.exists(image_source):
                return TargetFaceResult(success=False, message=f"File not found: {image_source}")
            img = cv2.imread(image_source)
            if img is None:
                return TargetFaceResult(success=False, message=f"Failed to decode image: {image_source}")
        elif isinstance(image_source, np.ndarray):
            img = image_source
        else:
            return TargetFaceResult(success=False, message="Invalid image source type.")

        h, w, _ = img.shape
        self.detector.setInputSize((w, h))
        faces = self.detector.detect(img)

        if faces[1] is None or len(faces[1]) == 0:
            return TargetFaceResult(success=False, message="No face detected in target image.")

        # ponytail: select face with highest detection confidence score
        best_idx = int(np.argmax(faces[1][:, 14]))
        best_face = faces[1][best_idx]

        aligned_crop = self.recognizer.alignCrop(img, best_face)
        feature_vector = self.recognizer.feature(aligned_crop)

        bbox = (int(best_face[0]), int(best_face[1]), int(best_face[2]), int(best_face[3]))
        score = float(best_face[14])

        with self._lock:
            self.target_crop = aligned_crop
            self.target_feature = feature_vector

        return TargetFaceResult(
            success=True,
            crop=aligned_crop,
            feature=feature_vector,
            bbox=bbox,
            score=score,
            message="Target face feature vector extracted successfully."
        )

    def load_video(self, video_path: str) -> Optional[VideoInfo]:
        """
        Open video file and extract metadata (FPS, total frames, resolution, duration).

        Args:
            video_path: File path to video file.

        Returns:
            VideoInfo object or None if video cannot be opened.
        """
        if not os.path.exists(video_path):
            return None

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None

        fps = float(cap.get(cv2.CAP_PROP_FPS))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = total_frames / fps if fps > 0 else 0.0

        cap.release()

        info = VideoInfo(
            video_path=video_path,
            fps=fps,
            total_frames=total_frames,
            width=width,
            height=height,
            duration=duration
        )
        self.video_info = info
        return info

    def start(self, video_path: str, target_image_source: Optional[Any] = None) -> bool:
        """
        Start processing worker thread on video in a thread-safe manner.

        Args:
            video_path: Video file path.
            target_image_source: Optional target image to load before starting.

        Returns:
            True if started successfully, False otherwise.
        """
        with self._lock:
            if self._state in (EngineState.RUNNING, EngineState.PAUSED):
                return False

        if target_image_source is not None:
            res = self.load_target_image(target_image_source)
            if not res.success:
                raise ValueError(f"Failed to set target image: {res.message}")

        if self.target_feature is None:
            raise ValueError("Target face feature vector not set. Load target image first.")

        info = self.load_video(video_path)
        if info is None or info.total_frames <= 0:
            raise ValueError(f"Could not open or read video: {video_path}")

        self._stop_event.clear()
        self._pause_event.set()
        self._set_state(EngineState.RUNNING)

        # ponytail: single worker thread used instead of multi-threaded producer-consumer queue for simplicity
        self._worker_thread = threading.Thread(
            target=self._process_loop,
            args=(video_path,),
            daemon=True
        )
        self._worker_thread.start()
        return True

    def pause(self) -> bool:
        """Pause worker thread processing."""
        with self._lock:
            if self._state != EngineState.RUNNING:
                return False
        self._pause_event.clear()
        self._set_state(EngineState.PAUSED)
        return True

    def resume(self) -> bool:
        """Resume worker thread processing."""
        with self._lock:
            if self._state != EngineState.PAUSED:
                return False
        self._pause_event.set()
        self._set_state(EngineState.RUNNING)
        return True

    def terminate(self) -> bool:
        """Terminate worker thread processing gracefully."""
        with self._lock:
            if self._state in (EngineState.TERMINATED, EngineState.COMPLETED, EngineState.IDLE):
                return False

        self._stop_event.set()
        self._pause_event.set()  # Unblock pause state wait
        self._set_state(EngineState.TERMINATED)

        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)
        return True

    def _process_loop(self, video_path: str) -> None:
        """Background worker thread processing loop."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            self._set_state(EngineState.COMPLETED)
            return

        width = self.video_info.width
        height = self.video_info.height
        total_frames = self.video_info.total_frames
        video_fps = self.video_info.fps if self.video_info.fps > 0 else 25.0

        # Set standard fast detection resolution (640x360) for high-speed YuNet inference
        det_w, det_h = 640, 360
        if width > 0 and height > 0:
            scale_x = width / det_w
            scale_y = height / det_h
        else:
            scale_x, scale_y = 1.0, 1.0

        self.detector.setInputSize((det_w, det_h))

        processed_frames = 0
        matches_count = 0
        start_time = time.time()
        total_paused_time = 0.0
        last_ui_update_time = 0.0

        while True:
            if self._stop_event.is_set():
                break

            # Handle pause state cleanly without spin-locking
            if not self._pause_event.is_set():
                pause_start = time.time()
                while not self._pause_event.is_set():
                    if self._stop_event.is_set():
                        break
                    time.sleep(0.05)
                total_paused_time += (time.time() - pause_start)
                if self._stop_event.is_set():
                    break

            ret, frame = cap.read()
            if not ret or frame is None:
                self._set_state(EngineState.COMPLETED)
                break

            frame_idx = processed_frames
            processed_frames += 1

            # High-speed detection on downscaled 640x360 frame
            det_frame = cv2.resize(frame, (det_w, det_h))
            faces = self.detector.detect(det_frame)
            detected_faces_count = 0

            if faces[1] is not None and len(faces[1]) > 0:
                detected_faces_count = len(faces[1])
                for face_row in faces[1]:
                    det_score = float(face_row[14])

                    # Scale face box back to original resolution frame for accurate SFace alignment & crop
                    scaled_face_row = face_row.copy()
                    scaled_face_row[0] *= scale_x  # x
                    scaled_face_row[1] *= scale_y  # y
                    scaled_face_row[2] *= scale_x  # w
                    scaled_face_row[3] *= scale_y  # h
                    scaled_face_row[4] *= scale_x  # right_eye_x
                    scaled_face_row[5] *= scale_y  # right_eye_y
                    scaled_face_row[6] *= scale_x  # left_eye_x
                    scaled_face_row[7] *= scale_y  # left_eye_y
                    scaled_face_row[8] *= scale_x  # nose_x
                    scaled_face_row[9] *= scale_y  # nose_y
                    scaled_face_row[10] *= scale_x # right_mouth_x
                    scaled_face_row[11] *= scale_y # right_mouth_y
                    scaled_face_row[12] *= scale_x # left_mouth_x
                    scaled_face_row[13] *= scale_y # left_mouth_y

                    aligned = self.recognizer.alignCrop(frame, scaled_face_row)
                    feat = self.recognizer.feature(aligned)

                    # Compute cosine similarity score using OpenCV SFace recognizer match
                    similarity = float(self.recognizer.match(self.target_feature, feat, cv2.FaceRecognizerSF_FR_COSINE))

                    # Check match condition (score >= cosine_threshold)
                    if similarity >= self.cosine_threshold:
                        matches_count += 1
                        bbox = (int(scaled_face_row[0]), int(scaled_face_row[1]), int(scaled_face_row[2]), int(scaled_face_row[3]))
                        ts_sec = frame_idx / video_fps

                        # Format timestamp (HH:MM:SS.mmm)
                        mins, secs = divmod(int(ts_sec), 60)
                        hrs, mins = divmod(mins, 60)
                        ms = int((ts_sec - int(ts_sec)) * 1000)
                        ts_str = f"{hrs:02d}:{mins:02d}:{secs:02d}.{ms:03d}"

                        match_res = MatchResult(
                            frame_index=frame_idx,
                            timestamp=ts_sec,
                            timestamp_str=ts_str,
                            similarity=similarity,
                            bbox=bbox,
                            face_crop=aligned,
                            score=det_score
                        )

                        if self.on_match_found:
                            try:
                                self.on_match_found(match_res)
                            except Exception:
                                pass

            # ETA and average FPS calculation based on active processing time
            now = time.time()
            elapsed_time = max(0.001, now - start_time - total_paused_time)
            current_fps = processed_frames / elapsed_time
            remaining_frames = max(0, total_frames - processed_frames)
            eta = remaining_frames / current_fps if current_fps > 0 else 0.0
            progress_pct = (processed_frames / total_frames * 100.0) if total_frames > 0 else 0.0

            # Throttle UI live preview updates to ~15 FPS max for zero GUI lag while processing at maximum speed
            if (now - last_ui_update_time >= 0.066) or (processed_frames == 1) or (processed_frames == total_frames):
                last_ui_update_time = now

                # Small 320x180 low-res preview frame without drawing bounding boxes (maximum speed)
                preview_frame = cv2.resize(frame, (320, 180))

                stats = FrameStats(
                    frame_index=frame_idx,
                    total_frames=total_frames,
                    processed_frames=processed_frames,
                    fps=current_fps,
                    elapsed_time=elapsed_time,
                    eta=eta,
                    progress_percent=progress_pct,
                    detected_faces_count=detected_faces_count,
                    matches_count=matches_count
                )

                if self.on_frame_update:
                    try:
                        self.on_frame_update(preview_frame, stats)
                    except Exception:
                        pass

        cap.release()

        # Finalize status state machine
        current_state = self.state
        if current_state not in (EngineState.TERMINATED, EngineState.COMPLETED):
            self._set_state(EngineState.COMPLETED)

        summary_stats = {
            "processed_frames": processed_frames,
            "total_frames": total_frames,
            "matches_count": matches_count,
            "elapsed_time": elapsed_time if 'elapsed_time' in locals() else 0.0,
            "average_fps": current_fps if 'current_fps' in locals() else 0.0,
            "final_state": self.state.value
        }

        if self.on_complete:
            try:
                self.on_complete(summary_stats)
            except Exception:
                pass


if __name__ == "__main__":
    print("=== Testing FaceEngine on alia.jpg and Sample Video ===")

    # 1. Initialize Engine
    engine = FaceEngine()
    print(f"Engine initialized with state: {engine.state.value}")

    # 2. Test Target Image Loader
    target_path = "alia.jpg"
    print(f"\nLoading target image: {target_path}")
    res = engine.load_target_image(target_path)
    print(f"Target Load Success: {res.success}")
    print(f"Target Message: {res.message}")
    if res.success:
        print(f"Target Bounding Box: {res.bbox}")
        print(f"Target Feature Vector Shape: {res.feature.shape}")
        print(f"Target Crop Shape: {res.crop.shape}")

    # 3. Test Video Loader
    video_path = "vidssave.com INDIA’S GOT LATENT S2 EP1 ft. Alia Bhatt, Sharvari, Ashish Solanki 1080P.mp4"
    print(f"\nLoading video info: {video_path}")
    info = engine.load_video(video_path)
    if info:
        print(f"FPS: {info.fps}")
        print(f"Total Frames: {info.total_frames}")
        print(f"Resolution: {info.width}x{info.height}")
        print(f"Duration: {info.duration:.2f} seconds ({info.duration/60:.2f} mins)")

    # 4. Configure Callbacks for Verification
    matches_logged = []
    status_history = []

    def handle_frame_update(frame: np.ndarray, stats: FrameStats):
        if stats.processed_frames % 10 == 0 or stats.matches_count > 0:
            print(f"[Frame {stats.processed_frames}/{stats.total_frames}] "
                  f"Progress: {stats.progress_percent:.2f}% | FPS: {stats.fps:.2f} | "
                  f"ETA: {stats.eta:.1f}s | Faces: {stats.detected_faces_count} | Matches: {stats.matches_count}")

    def handle_match_found(match: MatchResult):
        matches_logged.append(match)
        print(f"   ==> MATCH FOUND! Frame: {match.frame_index} | Time: {match.timestamp_str} | "
              f"Cosine Similarity: {match.similarity:.4f} | BBox: {match.bbox}")

    def handle_status_change(state: EngineState):
        status_history.append(state.value)
        print(f"[State Transition] --> Engine state changed to: {state.value}")

    def handle_complete(summary: dict):
        print(f"\n[Processing Complete] Summary: {summary}")

    engine.on_frame_update = handle_frame_update
    engine.on_match_found = handle_match_found
    engine.on_status_change = handle_status_change
    engine.on_complete = handle_complete

    # 5. Start Processing Thread & Test Pause/Resume/Terminate Controls
    print("\nStarting FaceEngine background worker thread...")
    engine.start(video_path)

    # Let it run for 1.5 seconds
    time.sleep(1.5)

    print("\n---> Testing PAUSE control...")
    engine.pause()
    time.sleep(1.0)
    print(f"Current State during Pause: {engine.state.value}")

    print("\n---> Testing RESUME control...")
    engine.resume()
    time.sleep(1.5)

    print("\n---> Testing TERMINATE control...")
    engine.terminate()
    print(f"Final State after Terminate: {engine.state.value}")

    print(f"\nStatus History: {status_history}")
    print(f"Total Matches Captured during test run: {len(matches_logged)}")
    print("\n=== FaceEngine Test Execution Completed Successfully ===")
