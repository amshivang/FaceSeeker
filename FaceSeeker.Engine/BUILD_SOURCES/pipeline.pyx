# ponytail: clean FaceSearchPipeline tying detector and recognizer together
# FIX: BUG-12 — threading.Lock around self.targets to prevent concurrent iteration/mutation crashes
import base64
import threading
import cv2
import numpy as np
from typing import List, Dict

try:
    from . import config
    from .result_models import FaceMatch
    from .detector import FaceDetector
    from .recognizer import FaceRecognizer
except ImportError:
    import config
    from result_models import FaceMatch
    from detector import FaceDetector
    from recognizer import FaceRecognizer

class FaceSearchPipeline:
    def __init__(self, yunet_model: str = None, sface_model: str = None, cosine_threshold: float = None):
        self.detector = FaceDetector(model_path=yunet_model)
        self.recognizer = FaceRecognizer(model_path=sface_model, cosine_threshold=cosine_threshold)
        self.targets: Dict[str, List[np.ndarray]] = {}
        self._lock = threading.Lock()

    def register_target(self, name: str, image: np.ndarray) -> bool:
        if image is None or image.size == 0:
            return False
        detections = self.detector.detect(image)
        if not detections:
            return False

        # Pick detection with highest confidence score (det[14])
        best_detection = max(detections, key=lambda d: float(d[14]) if len(d) > 14 else float(d[-1]))
        embedding = self.recognizer.extract(image, best_detection)
        if embedding is None:
            return False

        with self._lock:
            if name not in self.targets:
                self.targets[name] = []

            if len(self.targets[name]) >= config.MAX_TARGETS_PER_NAME:
                self.targets[name].pop(0)  # ponytail: simple FIFO cap
            self.targets[name].append(embedding)
        return True

    def clear_targets(self) -> None:
        with self._lock:
            self.targets.clear()

    def has_targets(self) -> bool:
        with self._lock:
            return len(self.targets) > 0

    def search_frame(self, frame: np.ndarray, frame_num: int, fps: float, video_path: str) -> List[FaceMatch]:
        results: List[FaceMatch] = []
        if frame is None:
            return results

        with self._lock:
            if not self.targets:
                return results
            # Snapshot targets reference for thread-safe iteration
            targets_snapshot = {name: list(embeddings) for name, embeddings in self.targets.items()}

        detections = self.detector.detect(frame)
        if not detections:
            return results

        H, W = frame.shape[:2]
        seconds = (frame_num / fps) if (fps and fps > 0) else 0.0
        timestamp_str = self._timestamp(seconds)

        for det in detections:
            embedding = self.recognizer.extract(frame, det)
            if embedding is None:
                continue

            for target_name, embeddings in targets_snapshot.items():
                if not embeddings:
                    continue
                max_score = max(self.recognizer.match_score(embedding, t_emb) for t_emb in embeddings)
                if max_score >= self.recognizer.cosine_threshold:
                    x = int(det[0])
                    y = int(det[1])
                    w = int(det[2])
                    h = int(det[3])

                    # Bounds clamping
                    x1 = max(0, min(x, W - 1))
                    y1 = max(0, min(y, H - 1))
                    x2 = max(x1 + 1, min(x + w, W))
                    y2 = max(y1 + 1, min(y + h, H))
                    crop = frame[y1:y2, x1:x2]

                    thumb_b64 = self._encode_thumbnail(crop)
                    match = FaceMatch(
                        target_name=target_name,
                        video_path=video_path,
                        frame_number=int(frame_num),
                        timestamp_str=timestamp_str,
                        confidence=round(float(max_score), 4),
                        thumbnail_b64=thumb_b64,
                        bbox=[x, y, w, h]
                    )
                    results.append(match)
        return results

    def _encode_thumbnail(self, crop: np.ndarray) -> str:
        if crop is None or crop.size == 0:
            return ""
        # Resize thumbnail if too large for fast socket transmission
        th_h, th_w = crop.shape[:2]
        if th_w > 120 or th_h > 120:
            scale = 120.0 / max(th_w, th_h)
            crop = cv2.resize(crop, (int(th_w * scale), int(th_h * scale)), interpolation=cv2.INTER_AREA)
        params = [int(cv2.IMWRITE_JPEG_QUALITY), config.THUMBNAIL_QUALITY]
        success, buf = cv2.imencode('.jpg', crop, params)
        if not success:
            return ""
        return base64.b64encode(buf).decode('ascii')

    def _timestamp(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"