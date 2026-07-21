# Implementation Plan 009: Animated Radar Scanning Empty State

**Goal**: Replace static empty text in the match gallery with an animated target scanning reticle/radar graphic during active analysis.

---

## Proposed UI Changes

### `ui.py`
- Add canvas or animated label in `match_scroll_frame` when state is `RUNNING` and `detected_matches` count is 0.
- Displays pulsating radar scan concentric circles with text `"Scanning video stream for target face..."`.

---

## Verification Plan
1. Start analysis -> verify animated scanning reticle appears in gallery until first match is found.
