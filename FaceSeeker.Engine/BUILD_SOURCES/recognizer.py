# ponytail: clean FaceRecognizer wrapping SFace with zero overhead
import cv2
import numpy as np
try:
    from . import config
except ImportError:
    import config

class FaceRecognizer:
    def __init__(self, model_path: str = None, cosine_threshold: float = None):
        model = model_path or config.SFACE_MODEL
        self.cosine_threshold = cosine_threshold if cosine_threshold is not None else config.COSINE_THRESHOLD
        self.recognizer = cv2.FaceRecognizerSF.create(
            model=model,
            config=""
        )

    def extract(self, frame: np.ndarray, detection: np.ndarray) -> np.ndarray:
        aligned = self.recognizer.alignCrop(frame, detection)
        feature = self.recognizer.feature(aligned)
        return feature

    def match_score(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        score = self.recognizer.match(embedding1, embedding2, cv2.FaceRecognizerSF_FR_COSINE)
        return float(score)

    def is_match(self, embedding1: np.ndarray, embedding2: np.ndarray) -> bool:
        score = self.match_score(embedding1, embedding2)
        return score >= self.cosine_threshold