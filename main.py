"""
main.py - Entry point for Face Seeker Standalone Windows Executable.
Handles sys._MEIPASS path resolution, model directory verification, and GUI launch.
"""

import os
import sys
import logging
import time
import threading
import webview
from pathlib import Path
from app import app

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


def start_flask():
    """Run Flask server in a background daemon thread."""
    logger.info("Launching FaceSeeker Web UI Backend...")
    # Run Flask without the reloader since we're bundling an app
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)


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

    # Start Flask backend in a separate thread
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()
    
    # Give Flask a moment to spin up before the window appears
    time.sleep(1.0)
    
    # 3. Launch PyWebView Native Window
    logger.info("Launching PyWebView Window...")
    icon_path = get_resource_path(os.path.join('assets', 'icon.ico'))
    if not os.path.exists(icon_path):
        logger.warning(f"Window icon not found at '{icon_path}'; using default.")
        icon_path = None

    window = webview.create_window(
        title='Face Seeker',
        url='http://127.0.0.1:5000',
        width=1200,
        height=800,
        min_size=(800, 600),
        background_color='#000000' # Matches fluent dark theme
    )

    webview.start(debug=False, icon=icon_path)


if __name__ == "__main__":
    main()
