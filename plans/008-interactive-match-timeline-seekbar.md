# Implementation Plan 008: Interactive Match Timeline Seekbar

**Goal**: Add a visual interactive video timeline seekbar directly below the video stream preview in `ui.py` with glowing timestamp match markers.

---

## Proposed UI Changes

### `ui.py`
- Add `CTkCanvas` or interactive slider timeline below passport video feed container.
- As matches are detected in `_analysis_worker`, draw glowing blue/green tick markers at the relative timestamp position along the timeline.
- Clicking any tick marker on the timeline jumps the live video label and stats to that frame.

---

## Verification Plan
1. Run analysis on video.
2. Click tick marker on timeline -> verify passport feed jumps to that match timestamp.
