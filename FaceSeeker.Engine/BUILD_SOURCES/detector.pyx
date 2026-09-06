# ponytail: clean FaceDetector wrapping YuNet with zero overhead
import cv2
import numpy as np
try:
    from . import config
except ImportError:
    import config

class FaceDetector:
    def __init__(self, model_path: str = None, score_threshold: float = None):
        model = model_path or config.YUNET_MODEL
        threshold = score_threshold if score_threshold is not None else config.DETECTION_CONF
        self.detector = cv2.FaceDetectorYN.create(
            model=model,
            config="",
            input_size=config.INPUT_SIZE,
            score_threshold=threshold,
            nms_threshold=0.3,
            top_k=5000
        )

    def detect(self, frame: np.ndarray) -> list:
        if frame is None or frame.size == 0:
            return []
        h, w = frame.shape[:2]
        self.detector.setInputSize((int(w), int(h)))
        _, faces = self.detector.detect(frame)
        if faces is None or len(faces) == 0:
            return []
        return [f for f in faces]