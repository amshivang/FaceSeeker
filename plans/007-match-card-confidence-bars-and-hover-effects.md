# Implementation Plan 007: Match Card Confidence Bars & Win11 Hover Animations

**Goal**: Enhance the Detected Matches Gallery in `ui.py` with color-coded confidence progress indicator bars and tactile Windows 11 hover border highlights.

---

## Proposed UI Changes

### `ui.py`
1. **Confidence Progress Bars**:
   - Inside `_add_match_card()`, add a thin CustomTkinter progress bar below each card's timestamp label.
   - Color code progress bar:
     - `≥ 80% Match`: `#107c41` (Win11 Green)
     - `70% - 79% Match`: `#0078d4` (Win11 Accent Blue)
     - `< 70% Match`: `#f59e0b` (Amber Warning)
2. **Win11 Tactile Card Hover Highlight**:
   - Bind `<Enter>` and `<Leave>` events on match cards:
     - Hover (`<Enter>`): Change `border_color` to `#0078d4` and `fg_color` to `#2e2e2e`.
     - Leave (`<Leave>`): Reset `border_color` to `#383838` and `fg_color` to `#252525`.

---

## Verification Plan

1. Launch application and run video scan.
2. Hover over match cards in gallery -> verify border highlights smoothly.
3. Check color coding on progress bars based on match confidence score.
