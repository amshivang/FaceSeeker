"""
create_project_overview_pdf.py - Generates a clean PDF overview of Face Seeker:
Project summary, working mechanism, tech stack table, and competitive comparison.
"""

import os
from fpdf import FPDF


def sanitize_str(text: str) -> str:
    if not text:
        return ""
    replacements = {
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "—": "-",
        "•": "-",
        "…": "...",
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)
    return text.encode("latin-1", "replace").decode("latin-1")


class ProjectOverviewPDF(FPDF):
    def header(self):
        self.set_y(15)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}  -  Face Seeker Architecture Overview", align="C")


def build_pdf():
    pdf = ProjectOverviewPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Section 1: Project Overview
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(0, 120, 212) # Win11 Accent Blue
    pdf.cell(0, 7, "1. Project Overview", new_x="LMARGIN", new_y="NEXT")
    pdf.set_line_width(0.5)
    pdf.set_draw_color(0, 120, 212)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(40, 40, 40)
    overview_text = (
        "Face Seeker is a 100% offline, air-gapped computer vision desktop application built for law enforcement "
        "and forensic investigators. It automates the task of scanning hours of surveillance video footage to "
        "locate specific target subjects, replacing manual video review with high-speed deep learning inference."
    )
    pdf.multi_cell(0, 5, sanitize_str(overview_text))
    pdf.ln(4)

    # Section 2: How It Works (Internal Working Mechanism)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(0, 120, 212)
    pdf.cell(0, 7, "2. How It Works (Internal Working Mechanism)", new_x="LMARGIN", new_y="NEXT")
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    steps = [
        ("Step 1: Target Ingestion & Vector Extraction", 
         "When a target photo is loaded, YuNet detects the face and SFace crops, aligns, and extracts a unique 128-dimensional floating-point feature vector representing the face structure."),
        
        ("Step 2: Video Frame Decoding & Dual Resolution Pipeline", 
         "Video frames are decoded frame-by-frame. Frames are downscaled to 640x360 for high-speed YuNet detection (achieving 35-50+ FPS). Bounding box coordinates are then mathematically scaled back to full 1080p resolution."),
        
        ("Step 3: Cosine Similarity Matching", 
         "SFace extracts a 128D vector for every face detected in the video frame. The engine computes the Cosine Similarity score against all loaded target vectors. If score >= Threshold (default 0.36), a match event is registered."),
        
        ("Step 4: Asynchronous Multi-Threading & Queue Dispatch", 
         "AI scanning runs on a dedicated background worker thread to prevent UI freezing. Frame updates, progress percentages, FPS, and match payloads stream asynchronously to the main GUI thread via a thread-safe Queue."),
        
        ("Step 5: High-Res Annotation & Report Generation", 
         "When a match is confirmed, the full 1080p frame is captured with bounding box coordinates and saved for side-by-side inspection, interactive seekbar plotting, and PDF incident report generation.")
    ]

    for title, desc in steps:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(0, 120, 212)
        pdf.cell(0, 5, sanitize_str(title), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(50, 50, 50)
        pdf.multi_cell(0, 4.5, sanitize_str(desc))
        pdf.ln(2.5)

    pdf.ln(2)

    # Section 3: Technology Stack
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(0, 120, 212)
    pdf.cell(0, 7, "3. Complete Technology Stack", new_x="LMARGIN", new_y="NEXT")
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    pdf.set_fill_color(43, 43, 43)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.cell(90, 6.5, "Component", border=1, align="C", fill=True)
    pdf.cell(100, 6.5, "Technology", border=1, align="C", fill=True)
    pdf.ln()

    stack_items = [
        ("Core Language", "Python 3.14"),
        ("Face Detection AI Model", "YuNet ONNX (OpenCV)"),
        ("Face Recognition AI Model", "SFace ONNX (OpenCV)"),
        ("Math & Matrix Engine", "NumPy"),
        ("GUI Desktop Framework", "CustomTkinter (Win11 Dark Theme)"),
        ("Image Processing Library", "Pillow (PIL)"),
        ("PDF Report Generator", "FPDF2"),
        ("Standalone Packaging", "PyInstaller 6.x")
    ]

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(30, 30, 30)

    for idx, (comp, tech) in enumerate(stack_items, 1):
        fill_bg = (idx % 2 == 0)
        pdf.set_fill_color(240, 240, 240) if fill_bg else pdf.set_fill_color(255, 255, 255)
        pdf.cell(90, 6, sanitize_str(comp), border=1, align="L", fill=fill_bg)
        pdf.cell(100, 6, sanitize_str(tech), border=1, align="L", fill=fill_bg)
        pdf.ln()

    # Section 4: Why Face Seeker is Better (Comparison with Existing Solutions)
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(0, 120, 212)
    pdf.cell(0, 7, "4. Why Face Seeker is Better (Comparison with Existing Solutions)", new_x="LMARGIN", new_y="NEXT")
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    pdf.set_fill_color(43, 43, 43)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.cell(38, 6.5, "Dimension", border=1, align="C", fill=True)
    pdf.cell(50, 6.5, "Typical GitHub Tools", border=1, align="C", fill=True)
    pdf.cell(50, 6.5, "Enterprise Software", border=1, align="C", fill=True)
    pdf.cell(52, 6.5, "Face Seeker (Our Solution)", border=1, align="C", fill=True)
    pdf.ln()

    comp_items = [
        ("Deployment", "Complex Python/dlib setup", "Expensive server contract", "Single Portable Executable (.exe)"),
        ("Model Overhead", "2GB - 5GB PyTorch/dlib", "Proprietary cloud models", "85KB + 37MB ONNX (Lightweight)"),
        ("Privacy & Security", "Variable (Some use web APIs)", "Cloud-connected servers", "100% Air-Gapped & Offline (0 Net)"),
        ("Processing Speed", "Slow (5 - 15 FPS CPU)", "Fast GPU Cluster", "35 - 50+ FPS (Optimized YuNet)"),
        ("Forensic Reporting", "Raw text output only", "Enterprise dashboards", "Side-by-side & PDF Reports")
    ]

    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(30, 30, 30)

    for idx, (feat, gh_val, ent_val, fs_val) in enumerate(comp_items, 1):
        fill_bg = (idx % 2 == 0)
        pdf.set_fill_color(240, 240, 240) if fill_bg else pdf.set_fill_color(255, 255, 255)
        pdf.cell(38, 6, sanitize_str(feat), border=1, align="L", fill=fill_bg)
        pdf.cell(50, 6, sanitize_str(gh_val), border=1, align="L", fill=fill_bg)
        pdf.cell(50, 6, sanitize_str(ent_val), border=1, align="L", fill=fill_bg)
        pdf.cell(52, 6, sanitize_str(fs_val), border=1, align="L", fill=fill_bg)
        pdf.ln()

    output_path = os.path.abspath("Face_Seeker_Project_Overview.pdf")
    pdf.output(output_path)
    print(f"PDF generated successfully at: {output_path}")

if __name__ == "__main__":
    build_pdf()
