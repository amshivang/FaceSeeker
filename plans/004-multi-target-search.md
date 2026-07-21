# Implementation Plan 004: Multi-Target Suspect Search

**Goal**: Extend Face Seeker to support loading up to 5 target suspect photos simultaneously, matching faces in a single video scan and color-coding detected matches per suspect.

---

## Proposed Architectural Changes

1. **`face_engine.py`**:
   - `self.target_features`: List of `TargetFaceResult` objects (Suspect A, Suspect B, etc.).
   - During frame scanning, compare detected face embeddings against all loaded target feature vectors.
   - Return suspect ID / index in `MatchResult`.

2. **`ui.py`**:
   - Target Image section becomes a multi-slot list/card selector (`[ + Add Target ]`).
   - Match Gallery displays suspect badge labels (e.g. `Target #1 (89%)`, `Target #2 (91%)`).

---

## Verification Plan
1. Add 2 target images (`alia.jpg` and second target image).
2. Scan video and verify matches for both targets are detected and labeled correctly.
