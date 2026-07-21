# Implementation Plan 001: Automated Test Suite Baseline

**Goal**: Establish a single-command automated test suite baseline (`tests/`) using Python `unittest` for `face_engine.py` and `ui.py` resource resolution, model initialization, and matching engine logic.

---

## Target Files

### [NEW] `tests/test_face_engine.py`
Unit tests for `face_engine.py`:
- `get_resource_path()` resolution.
- `FaceEngine` initialization with ONNX models.
- Target face extraction and 128D embedding shape `(1, 128)`.
- Cosine similarity matching logic.
- Engine state transitions (`IDLE` -> `RUNNING` -> `PAUSED` -> `TERMINATED`).

### [NEW] `tests/test_ui_paths.py`
Unit tests for `ui.py` path resolvers, model checks, and helper functions.

---

## Verification Command

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

Expected Output:
```
Ran X tests in Y.YYYs
OK
```

---

## Step-by-Step Implementation

1. Create `tests/__init__.py`.
2. Create `tests/test_face_engine.py`:
   - Test target face loading on `alia.jpg` -> assert `res.success` is True.
   - Test feature shape -> assert `res.feature.shape == (1, 128)`.
   - Test video metadata loading on sample video -> assert `info.total_frames > 0`.
3. Create `tests/test_ui_paths.py`:
   - Test `get_resource_path("models/face_detection_yunet_2023mar.onnx")` exists.
4. Run `python -m unittest discover -s tests` to verify all tests pass.
