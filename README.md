# 🛡️ Face Seeker — Target Face Detector for Law Enforcement & Forensic Analysis

[![Python Version](https://img.shields.io/badge/python-3.14-blue.svg)](https://python.org)
[![OpenCV](https://img.shields.io/badge/OpenCV-YuNet%20%2B%20SFace-green.svg)](https://opencv.org)
[![Offline Security](https://img.shields.io/badge/Security-100%25%20Offline%20Air--Gapped-success.svg)](#)
[![UI Theme](https://img.shields.io/badge/UI-Windows%2011%20Fluent%20Dark-0078d4.svg)](#)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Face Seeker** is a 100% offline, air-gapped computer vision desktop application engineered for law enforcement agencies, forensic investigators, and security teams. It automates the task of scanning hours of surveillance CCTV footage to locate specific target subjects, replacing manual video review with high-speed deep learning inference (**35 - 50+ FPS**).

---

## ✨ Key Features

- **100% Air-Gapped & Offline Security**: Zero internet connection, zero external API calls, and zero remote dependencies required. Perfect for high-security forensic networks.
- **Multi-Target Parallel Matching**: Load multiple suspect photographs simultaneously (`Target #1`, `Target #2`, etc.) and match them in a single video scan pass.
- **High-Speed AI Processing Pipeline**: Runs at **35 - 50+ FPS** by utilizing downscaled YuNet detection size (`640x360`) mapped back to full 1080p high-resolution frame alignment.
- **Interactive Video Seekbar & Timeline**: Glowing tick markers plot along the timeline as matches are detected. Clicking any tick marker jumps directly to that match timestamp.
- **Side-by-Side Detail Inspector**: Displays the suspect photo side-by-side with the video face crop and match percentage (`94.8% Match`).
- **Court-Ready PDF Incident Reports**: Exports official, formatted evidence documents with law enforcement headers, video specifications, target metadata, and complete match event logs.
- **Target Image Quality & Pose Diagnostics**: Calculates facial image sharpness using Laplacian variance (`cv2.Laplacian`) to alert investigators if a target photo is blurry or low resolution.
- **Batch Video Folder Scanner**: Queue and process an entire directory of CCTV video recordings (`.mp4`, `.avi`, `.mkv`) sequentially.

---

## 🛠️ Complete Technology Stack

| Layer / Component | Technology | Role / Rationale |
|---|---|---|
| **Core Runtime** | Python 3.14 | Core runtime and asynchronous multi-threading engine |
| **Face Detection AI** | YuNet ONNX (OpenCV) | Ultra-lightweight (85KB) neural network for fast 640x360 face detection |
| **Face Recognition AI** | SFace ONNX (OpenCV) | Deep CNN extracting 128D feature vectors for Cosine Similarity matching ($\ge 0.363$) |
| **Math & Matrix Engine** | NumPy | High-performance vector math & array transformations |
| **GUI Framework** | CustomTkinter | Windows 11 Native Fluent Dark Theme (`#202020` Mica dark gray base) |
| **Image Processing** | Pillow (PIL) | Canvas scaling & bounding box drawing (`ImageDraw`) |
| **PDF Reporting** | FPDF2 | Lightweight PDF incident report generator |
| **Standalone Packaging**| PyInstaller 6.x | Bundles 100% self-contained `FaceSeeker.exe` standalone executable |

---

## ⚡ How It Works (Internal Pipeline)

1. **Target Subject Vector Extraction**: When a target photo is uploaded, YuNet detects the face and SFace extracts a unique 128-dimensional floating-point feature vector.
2. **Dual-Resolution Decoding**: Video frames are downscaled to `640x360` for fast YuNet inference (35-50+ FPS). Bounding box coordinates are mathematically scaled back to full 1080p resolution.
3. **Cosine Similarity Matching**: SFace computes Cosine Similarity against all loaded target vectors. If similarity $\ge$ threshold, a match event is logged.
4. **Asynchronous Queue Dispatching**: AI scanning runs on a background worker thread, streaming updates via a thread-safe Queue to keep the UI fluid.
5. **High-Res Reporting & Inspection**: Confirmed match frames are captured in 1080p, rendered in the side-by-side inspector, seekbar, and PDF reports.

---

## 🚀 Quick Start (Running the Standalone App)

No installation or Python environment required!

1. Download `FaceSeeker.exe` from the latest [Releases](../../releases).
2. Double-click **`FaceSeeker.exe`** to launch.
3. Click **`➕ Add Target Subject`** to select suspect photo(s).
4. Click **`🎥 Select Video File / Folder`** to load CCTV recording(s).
5. Click **`🚀 Start Analysis`**.

---

## 📄 Building From Source

```bash
# Clone repository
git clone https://github.com/your-username/FaceSeeker.git
cd FaceSeeker

# Install dependencies
pip install opencv-python customtkinter pillow numpy fpdf2 pyinstaller

# Run application
python main.py

# Build standalone executable
pyinstaller face_seeker.spec --noconfirm
```

---

## 📜 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---
<div align="center">
  <a href="https://buymeacoffee.com/amshivang">
    <img src="https://raw.githubusercontent.com/amshivang/amshivang/main/qr-code.png" alt="Buy Me A Coffee" width="200">
  </a>
  <br>
  <strong><a href="https://buymeacoffee.com/amshivang">Support my work on Buy Me A Coffee! ☕</a></strong>
</div>

