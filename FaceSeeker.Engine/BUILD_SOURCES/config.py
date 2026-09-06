# ponytail: clean module-level configuration with robust model path discovery
import os

_current_dir = os.path.dirname(os.path.abspath(__file__))

def _resolve_model(filename: str) -> str:
    candidates = [
        os.path.join(_current_dir, "..", "..", "models", filename),
        os.path.join(_current_dir, "..", "models", filename),
        os.path.join(os.getcwd(), "models", filename),
        os.path.join(os.path.dirname(_current_dir), "models", filename),
    ]
    for c in candidates:
        norm = os.path.abspath(c)
        if os.path.isfile(norm):
            return norm
    return os.path.abspath(os.path.join(_current_dir, "..", "..", "models", filename))

YUNET_MODEL = _resolve_model("face_detection_yunet_2023mar.onnx")
SFACE_MODEL = _resolve_model("face_recognition_sface_2021dec.onnx")

DETECTION_CONF = 0.85
COSINE_THRESHOLD = 0.363
FRAME_SKIP = 5
INPUT_SIZE = (320, 320)
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 54321
THUMBNAIL_QUALITY = 80
MAX_TARGETS_PER_NAME = 5