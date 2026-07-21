# Implementation Plan 002: Consolidate Face Engine Architecture

**Goal**: Consolidate duplicated video processing and ONNX model instantiation logic between `ui.py`'s `_analysis_worker()` and `face_engine.py`'s `FaceEngine` class.

---

## Current Problem
- `ui.py` currently duplicates `cv2.FaceDetectorYN` and `cv2.FaceRecognizerSF` creation inside `_analysis_worker()`, bypassing the `FaceEngine` class in `face_engine.py`.
- This causes code drift between `face_engine.py` and `ui.py` whenever detection sizes, threshold updates, or GPU backends are modified.

---

## Proposed Changes

### `ui.py`
- Replace `_analysis_worker()` inner loops with an instance of `FaceEngine` from `face_engine.py`.
- Bind `engine.on_frame_update` and `engine.on_match_found` directly to `ui.py`'s GUI thread queue dispatcher (`msg_queue.put`).
- Simplify `_start_analysis`, `_pause_analysis`, `_resume_analysis`, and `_terminate_analysis` to invoke `self.engine.start()`, `self.engine.pause()`, `self.engine.resume()`, and `self.engine.terminate()`.

---

## Verification Plan

### Automated Tests
```powershell
python -m unittest discover -s tests
```

### Manual Verification
1. Launch `python main.py`.
2. Select target image and video.
3. Verify Start -> Pause -> Resume -> Terminate controls work seamlessly via `FaceEngine` callbacks.
