# Implementation Plan 005: Batch Video Folder Queue Scanner

**Goal**: Add automated multi-video batch scanning mode so users can select an entire directory containing multiple CCTV video files and scan them sequentially.

---

## Proposed Architectural Changes

1. **`ui.py`**:
   - Add `📁 Select Video Folder` option alongside single video file picker.
   - Display video queue list (`0/5 Videos Processed`).
   - Sequentially pass each video file to `FaceEngine` and aggregate match findings into a unified multi-video report.

---

## Verification Plan
1. Select folder containing 2+ video files.
2. Click `Start Analysis` -> verify Queue progresses automatically through all videos.
