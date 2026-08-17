# 🛡️ Face Seeker — Target Face Detector for Law Enforcement & Forensic Analysis

[![Python Version](https://img.shields.io/badge/python-3.14-blue.svg)](https://python.org)
[![OpenCV](https://img.shields.io/badge/OpenCV-YuNet%20%2B%20SFace-green.svg)](https://opencv.org)
[![Offline Security](https://img.shields.io/badge/Security-100%25%20Offline%20Air--Gapped-success.svg)](#)
[![UI Theme](https://img.shields.io/badge/UI-PyWebView%20Native%20App-0078d4.svg)](#)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Face Seeker** is a 100% offline, air-gapped computer vision desktop application engineered for law enforcement agencies, forensic investigators, and security teams. It automates the task of scanning hours of surveillance CCTV footage to locate specific target subjects, replacing manual video review with high-speed deep learning inference (**35 - 50+ FPS**).

---

## ✨ Key Features

- **100% Air-Gapped & Offline Security**: Zero internet connection, zero external API calls, and zero remote dependencies required. Perfect for high-security forensic networks.
- **Multi-Target Parallel Matching**: Load multiple suspect photographs simultaneously (`Target #1`, `Target #2`, etc.). Every detected face is compared against *all* loaded targets in a single video scan pass and attributed to whichever target is the closest match.
- **High-Speed AI Processing Pipeline**: Runs at **35 - 50+ FPS** by utilizing downscaled YuNet detection size (`640x360`) mapped back to full 1080p high-resolution frame alignment. An optional **Processing Speed** control (Thorough / Balanced / Fast) trades temporal resolution for even higher throughput on very long archives. Automatically uses CUDA GPU acceleration when the installed OpenCV build supports it, falling back to CPU otherwise.
- **Live Annotated Preview**: The live scan feed draws bounding boxes around every detected face in real time — green for a confirmed match (with target name & confidence), amber otherwise — so investigators can visually verify the AI is working correctly, not just trust a black box.
- **Interactive Video Seekbar & Timeline**: Glowing tick markers plot along the timeline as matches are detected. Clicking any tick marker (or anywhere on the bar) switches to the native **Review** player and seeks directly to that timestamp — full scrubbing, play/pause, and frame-accurate review of the original footage.
- **Side-by-Side Detail Inspector**: Click any match card to open a modal comparing the suspect photo directly against the video face crop, with match percentage (`94.8% Match`) and a one-click "Jump to This Moment" action.
- **Target Image Quality & Pose Diagnostics**: Calculates facial image sharpness using Laplacian variance (`cv2.Laplacian`) to warn investigators in-app if a target photo is blurry or low resolution and likely to reduce match reliability.
- **Batch Video Folder Scanner**: Queue an entire directory of CCTV recordings (`.mp4`, `.avi`, `.mkv`, `.mov`) and scan them sequentially and automatically, with a live queue/progress view and no manual intervention between files.
- **Evidentiary CSV Export**: One-click export of every match found in the session — video file, target, timestamp, frame index, similarity %, and detection confidence — for chain-of-custody documentation.
- **Privacy-Conscious by Default**: Suspect photos and match face crops are written only to a local `uploads/` folder and are automatically purged at every application startup, so sensitive imagery never silently accumulates on disk between investigations.

---

## 🛠️ Complete Technology Stack

| Layer / Component | Technology | Role / Rationale |
|---|---|---|
| **Core Runtime** | Python 3.14 | Core runtime and asynchronous multi-threading engine |
| **Face Detection AI** | YuNet ONNX (OpenCV) | Ultra-lightweight (85KB) neural network for fast 640x360 face detection |
| **Face Recognition AI** | SFace ONNX (OpenCV) | Deep CNN extracting 128D feature vectors for Cosine Similarity matching ($\ge 0.363$) |
| **Math & Matrix Engine** | NumPy | High-performance vector math & array transformations |
| **GUI Framework** | PyWebView & Flask | Native Windows standalone container wrapping an HTML5/CSS/JS frontend |
| **Standalone Packaging**| PyInstaller 6.x | Bundles 100% self-contained `FaceSeeker.exe` standalone executable |

---

## ⚡ How It Works (Internal Pipeline)

1. **Target Subject Vector Extraction**: For every target photo added, YuNet detects the face, SFace aligns and extracts a unique 128-dimensional feature vector, and a Laplacian-variance sharpness score flags low-quality photos.
2. **Dual-Resolution Decoding**: Video frames are downscaled to `640x360` for fast YuNet inference (35-50+ FPS). Bounding box coordinates are mathematically scaled back to full 1080p resolution for accurate face alignment and cropping.
3. **Multi-Target Cosine Similarity Matching**: SFace computes Cosine Similarity between each detected face and every loaded target vector. The best-scoring target above the configured threshold is logged as a match.
4. **Asynchronous Queue Dispatching**: AI scanning runs on a background worker thread, streaming frame previews (with detection overlays) and stats updates via thread-safe queues (MJPEG + Server-Sent Events) to keep the UI fluid.
5. **High-Res Inspection & Review**: Confirmed match frames are captured in full resolution, rendered in the side-by-side inspector, plotted on the interactive timeline, and remain seekable in the native Review video player after (or during) a scan.

---

## 🚀 Quick Start (Running the Standalone App)

No installation or Python environment required!

1. Download `FaceSeeker.exe` from the latest [Releases](../../releases).
2. Double-click **`FaceSeeker.exe`** to launch.
3. Click **`Add Target Photo`** (repeatable) to load one or more suspect photos.
4. Click **`Select Video`** for a single file, or **`Select Folder`** to queue a batch of recordings.
5. Click **`Start Analysis`**.
6. Click any match card to inspect it side-by-side, or any timeline marker to jump straight to that moment in the Review player.
7. Click **`Export`** to download a CSV report of every match found.

---

## 📄 Building From Source

```bash
# Clone repository
git clone https://github.com/your-username/FaceSeeker.git
cd FaceSeeker

# Install dependencies
pip install -r requirements.txt

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
