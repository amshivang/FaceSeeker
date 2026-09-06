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

    def detect(self, frame: np.ndarray, max_dim: int = 640) -> list:
        if frame is None or frame.size == 0:
            return []
        h, w = frame.shape[:2]
        if max(h, w) > max_dim:
            scale = max_dim / float(max(h, w))
            det_w = int(round(w * scale))
            det_h = int(round(h * scale))
            det_frame = cv2.resize(frame, (det_w, det_h), interpolation=cv2.INTER_AREA)
            self.detector.setInputSize((det_w, det_h))
            _, faces = self.detector.detect(det_frame)
            if faces is None or len(faces) == 0:
                return []
            inv_scale = 1.0 / scale
            scaled_faces = []
            for f in faces:
                sf = f.copy()
                sf[0:4] = sf[0:4] * inv_scale
                sf[4:14] = sf[4:14] * inv_scale
                scaled_faces.append(sf)
            return scaled_faces
        else:
            self.detector.setInputSize((int(w), int(h)))
            _, faces = self.detector.detect(frame)
            if faces is None or len(faces) == 0:
                return []
            return [f for f in faces]