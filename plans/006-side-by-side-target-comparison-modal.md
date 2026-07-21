# Implementation Plan 006: Side-by-Side Target Comparison in Match Detail Modal

**Goal**: Redesign the `MatchPreviewModal` in `ui.py` to feature a prominent side-by-side target subject photo vs detected face crop comparison card with a central similarity gauge pill, providing instant visual verification for law enforcement officers.

---

## Target Files

### `ui.py`
- Modify `MatchPreviewModal._build_ui()`:
  - Add a top comparison banner inside the sidebar or header:
    - **Left Box**: Target Subject Image (cropped/aligned).
    - **Center Box**: Match Confidence Gauge (e.g. `94.8% SIMILARITY`, color-coded green/blue).
    - **Right Box**: Detected Face Crop from Video Frame.
  - Retain full high-res annotated frame preview with interactive zoom/scale.

---

## Verification Plan

1. Run analysis and click `🔍 Details` on any detected match card.
2. Verify side-by-side comparison panel displays both target and detected faces with match score gauge.
