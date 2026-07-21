"""
main.py - Entry point for Face Seeker Standalone Windows Executable.
Handles sys._MEIPASS path resolution, model directory verification, and GUI launch.
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging for application lifecycle
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(asctime)s - %(name)s - %(message)s"
)
logger = logging.getLogger("FaceSeekerMain")


def get_resource_path(relative_path: str) -> str:
    """
    Get absolute path to resource, supporting PyInstaller bundle sys._MEIPASS
    as well as standard development environment.
    
    Args:
        relative_path: Relative path to resource (e.g., 'models/face_detection_yunet_2023mar.onnx')
        
    Returns:
        Absolute normalized path string.
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


def ensure_models_dir() -> str:
    """
    Check and verify models directory and essential ONNX models.
    Creates models directory if missing and logs model availability status.
    
    Returns:
        Absolute path to verified models directory.
    """
    models_dir = get_resource_path("models")
    
    if not os.path.exists(models_dir):
        logger.info(f"Models directory not found at '{models_dir}'. Creating directory...")
        os.makedirs(models_dir, exist_ok=True)
    
    expected_models = [
        "face_detection_yunet_2023mar.onnx",
        "face_recognition_sface_2021dec.onnx"
    ]
    
    for model_name in expected_models:
        model_path = os.path.join(models_dir, model_name)
        if os.path.exists(model_path):
            logger.info(f"Verified required model: {model_name} ({os.path.getsize(model_path)} bytes)")
        else:
            logger.warning(f"Model file missing: '{model_name}' at {model_path}")
            
    return models_dir


def main():
    """
    Main application startup sequence.
    """
    logger.info("Initializing Face Seeker execution context...")

    # Set working directory and module search path for frozen PyInstaller environment
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        logger.info(f"Running in PyInstaller bundle mode. MEIPASS root: {sys._MEIPASS}")
        os.chdir(sys._MEIPASS)
        if sys._MEIPASS not in sys.path:
            sys.path.insert(0, sys._MEIPASS)
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))
        logger.info(f"Running in standard Python environment. App root: {app_dir}")
        if app_dir not in sys.path:
            sys.path.insert(0, app_dir)

    # Verify models directory and ONNX files
    models_dir = ensure_models_dir()
    logger.info(f"Models directory verified at: {models_dir}")

    # Launch UI application from ui.py
    logger.info("Importing FaceSeekerApp interface from ui module...")
    try:
        from ui import FaceSeekerApp
    except ImportError as e:
        logger.warning(f"Could not import FaceSeekerApp directly: {e}. Trying FaceSeekerUI...")
        from ui import FaceSeekerUI as FaceSeekerApp

    logger.info("Launching FaceSeeker GUI main loop...")
    app = FaceSeekerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
