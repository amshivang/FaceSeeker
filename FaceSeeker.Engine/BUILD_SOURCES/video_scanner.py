# ponytail: clean VideoScanner frame loop with minimal overhead
# FIX: LEAK-05 — try/finally ensures cap.release() even on exception
import os
import cv2
from typing import Callable, List, Optional

try:
    from .result_models import VideoComplete, FaceMatch
    from .pipeline import FaceSearchPipeline
except ImportError:
    from result_models import VideoComplete, FaceMatch
    from pipeline import FaceSearchPipeline

class VideoScanner:
    def __init__(self, pipeline: FaceSearchPipeline, frame_skip: int = 5):
        self.pipeline = pipeline
        self.frame_skip = max(1, frame_skip)

    def scan(
        self,
        video_path: str,
        on_match_cb: Optional[Callable[[FaceMatch], None]] = None,
        on_progress_cb: Optional[Callable[[str, int, int], None]] = None,
        cancel_flag = None
    ) -> VideoComplete:
        if not os.path.isfile(video_path):
            return VideoComplete(video_path=video_path, total_matches=0, error=f"File not found: {video_path}")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return VideoComplete(video_path=video_path, total_matches=0, error="Failed to open video")

        raw_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        total_frames = int(raw_frames) if raw_frames > 0 and raw_frames == raw_frames else 0
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0 or fps != fps:  # handle NaN or <= 0
            fps = 30.0

        frame_number = 0
        total_matches = 0
        error = ""

        try:
            while True:
                if cancel_flag and cancel_flag[0]:
                    break

                ret, frame = cap.read()
                if not ret:
                    break

                if frame_number % self.frame_skip == 0:
                    try:
                        matches = self.pipeline.search_frame(frame, frame_number, fps, video_path)
                        for match in matches:
                            total_matches += 1
                            if on_match_cb:
                                on_match_cb(match)
                    except Exception as e:
                        error = f"Frame {frame_number} error: {e}"

                    if on_progress_cb:
                        on_progress_cb(video_path, frame_number, total_frames)

                frame_number += 1
        except Exception as e:
            error = f"Scan error: {e}"
        finally:
            cap.release()

        return VideoComplete(video_path=video_path, total_matches=total_matches, error=error)