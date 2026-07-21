# Implementation Plan 003: Court-Ready PDF Incident Report Export

**Goal**: Add an official, print-ready PDF Incident Report Export feature using `fpdf2` (already installed in environment), replacing/complementing the raw CSV export.

---

## Target Files

### [NEW] `pdf_exporter.py`
- Implements `generate_pdf_report(target_image_path, match_list, video_meta, output_path)`:
  - Header: Law Enforcement / Official Forensic Report Banner with Timestamp and Date.
  - Section 1: Case & Target Information (Target Photo thumbnail, File Name, Image Dimensions).
  - Section 2: Video Metadata (Video Name, Resolution, FPS, Duration, Total Frames Scanned).
  - Section 3: Summary Statistics (Total Matches Found, Highest Match Confidence %, Scanning Time).
  - Section 4: Match Event Table & Snapshots:
    - Grid/Table showing Match #, Timestamp (HH:MM:SS), Frame #, Cosine Similarity %, and Cropped Face Snapshot Image!

### `ui.py`
- Add `📥 Export PDF Report` button in Detected Matches Gallery header.
- Wire `_export_matches_pdf()` method opening a file dialog saving `.pdf` report.

---

## Verification Plan

1. Run analysis to detect target matches.
2. Click `📥 Export PDF Report` -> Save `face_seeker_report.pdf`.
3. Open PDF file and verify formatting, images, and tables.
