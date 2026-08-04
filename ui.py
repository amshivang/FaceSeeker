import os
import sys
import cv2
import time
import csv
import queue
import threading
from datetime import datetime, timedelta
import numpy as np
from PIL import Image, ImageTk, ImageDraw

import customtkinter as ctk
from tkinter import filedialog, messagebox

from pdf_exporter import generate_pdf_report

# Windows 11 Fluent Dark Theme Configuration
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


def get_resource_path(relative_path: str) -> str:
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    full_path = os.path.join(base_path, relative_path)
    if os.path.exists(full_path):
        return full_path
    cwd_path = os.path.abspath(relative_path)
    if os.path.exists(cwd_path):
        return cwd_path
    return os.path.abspath(full_path)


class MatchPreviewModal(ctk.CTkToplevel):
    """
    Windows 11 Styled Modal Inspector featuring Side-by-Side Target Face vs Detected Face Comparison
    and full high-res annotated frame preview with interactive zoom/scale.
    """

    def __init__(self, parent, match_data):
        super().__init__(parent)
        self.match_data = match_data  # dict: {timestamp_str, frame_idx, score, frame_img, bbox, crop_img, target_info}

        target_name = match_data.get("target_name", "Target Subject")
        self.title(f"Match Detail Viewer - {target_name} ({match_data['timestamp_str']})")
        self.geometry("1020x720")
        self.minsize(880, 600)
        self.configure(fg_color="#202020")  # Win11 Mica Base Dark Gray

        self.transient(parent)
        self.grab_set()
        self.after(100, self.lift)

        self._build_ui()

    def _build_ui(self):
        header_frame = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=8, border_width=1, border_color="#3a3a3a")
        header_frame.pack(fill="x", padx=15, pady=(15, 10))

        target_name = self.match_data.get("target_name", "Target Subject")
        lbl_title = ctk.CTkLabel(
            header_frame,
            text=f"🔍 Target Match Details  •  {target_name}  •  Timestamp: {self.match_data['timestamp_str']}  •  Frame #{self.match_data['frame_idx']}",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#ffffff"
        )
        lbl_title.pack(side="left", padx=15, pady=12)

        score_pct = self.match_data['score'] * 100.0
        badge_lbl = ctk.CTkLabel(
            header_frame,
            text=f"  {score_pct:.1f}% MATCH CONFIDENCE  ",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#0078d4",
            text_color="#ffffff",
            corner_radius=6
        )
        badge_lbl.pack(side="right", padx=15, pady=12)

        # TOP SIDE-BY-SIDE FACE COMPARISON PANEL
        cmp_panel = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=8, border_width=1, border_color="#3a3a3a")
        cmp_panel.pack(fill="x", padx=15, pady=(0, 10))

        cmp_inner = ctk.CTkFrame(cmp_panel, fg_color="transparent")
        cmp_inner.pack(expand=True, pady=12)

        # Left: Target Subject Photo Crop
        left_box = ctk.CTkFrame(cmp_inner, fg_color="#1f1f1f", corner_radius=6, border_width=1, border_color="#383838")
        left_box.pack(side="left", padx=20)

        lbl_l_tag = ctk.CTkLabel(left_box, text=f"👤 {target_name}", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="#adadad")
        lbl_l_tag.pack(pady=(6, 2))

        target_crop = self.match_data.get("target_crop_pil")
        if target_crop is None:
            target_crop = Image.new("RGB", (90, 90), "#383838")

        target_crop_ctk = ctk.CTkImage(light_image=target_crop, dark_image=target_crop, size=(90, 90))
        lbl_target_img = ctk.CTkLabel(left_box, image=target_crop_ctk, text="")
        lbl_target_img.pack(padx=10, pady=(0, 8))

        # Center: Match Similarity Gauge
        center_box = ctk.CTkFrame(cmp_inner, fg_color="transparent")
        center_box.pack(side="left", padx=20)

        lbl_vs = ctk.CTkLabel(center_box, text="⚡ SIMILARITY MATCH ⚡", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#0078d4")
        lbl_vs.pack()

        gauge_badge = ctk.CTkLabel(
            center_box,
            text=f"  {score_pct:.1f}%  ",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            fg_color="#0078d4",
            text_color="#ffffff",
            corner_radius=8,
            padx=16,
            pady=4
        )
        gauge_badge.pack(pady=4)

        lbl_status = ctk.CTkLabel(center_box, text="CONFIRMED TARGET MATCH", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="#107c41")
        lbl_status.pack()

        # Right: Detected Face Crop
        right_box = ctk.CTkFrame(cmp_inner, fg_color="#1f1f1f", corner_radius=6, border_width=1, border_color="#383838")
        right_box.pack(side="left", padx=20)

        lbl_r_tag = ctk.CTkLabel(right_box, text="Detected Video Crop", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="#adadad")
        lbl_r_tag.pack(pady=(6, 2))

        det_crop = self.match_data.get("crop_img")
        if det_crop is None:
            det_crop = Image.new("RGB", (90, 90), "#383838")

        det_crop_ctk = ctk.CTkImage(light_image=det_crop, dark_image=det_crop, size=(90, 90))
        lbl_det_img = ctk.CTkLabel(right_box, image=det_crop_ctk, text="")
        lbl_det_img.pack(padx=10, pady=(0, 8))

        # Main content area
        main_content = ctk.CTkFrame(self, fg_color="transparent")
        main_content.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        preview_container = ctk.CTkFrame(main_content, fg_color="#2b2b2b", corner_radius=8, border_width=1, border_color="#3a3a3a")
        preview_container.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self.canvas_label = ctk.CTkLabel(preview_container, text="", fg_color="#000000", corner_radius=6)
        self.canvas_label.pack(fill="both", expand=True, padx=10, pady=10)

        self.annotated_image = self._render_annotated_frame()
        self._update_modal_image()
        self.canvas_label.bind("<Configure>", lambda e: self._update_modal_image())

        # Detailed Info Sidebar
        sidebar = ctk.CTkFrame(main_content, width=260, fg_color="#2b2b2b", corner_radius=8, border_width=1, border_color="#3a3a3a")
        sidebar.pack(side="right", fill="y")

        lbl_side_heading = ctk.CTkLabel(
            sidebar,
            text="Frame Properties",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#ffffff"
        )
        lbl_side_heading.pack(anchor="w", padx=15, pady=(15, 10))

        info_items = [
            ("Target Subject:", target_name),
            ("Video Timestamp:", self.match_data["timestamp_str"]),
            ("Frame Sequence #:", str(self.match_data["frame_idx"])),
            ("Similarity Score:", f"{score_pct:.2f}%"),
            ("Bounding Box (XYWH):", str(self.match_data.get("bbox", "N/A"))),
            ("Source Video:", os.path.basename(self.match_data.get("video_source", "Video.mp4"))),
        ]

        for label_text, val_text in info_items:
            item_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
            item_frame.pack(fill="x", padx=15, pady=4)
            lbl = ctk.CTkLabel(item_frame, text=label_text, font=ctk.CTkFont(family="Segoe UI", size=11), text_color="#adadad")
            lbl.pack(anchor="w")
            val = ctk.CTkLabel(item_frame, text=val_text, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#ffffff")
            val.pack(anchor="w")

        btn_save = ctk.CTkButton(
            sidebar,
            text="💾 Save High-Res Frame",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#0078d4",
            hover_color="#005a9e",
            corner_radius=6,
            height=36,
            command=self._save_frame
        )
        btn_save.pack(fill="x", padx=15, pady=(20, 8))

        btn_close = ctk.CTkButton(
            sidebar,
            text="✖️ Close Modal",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#3a3a3a",
            hover_color="#454545",
            corner_radius=6,
            height=32,
            command=self.destroy
        )
        btn_close.pack(fill="x", padx=15, pady=(0, 15))

    def _render_annotated_frame(self):
        frame_pil = self.match_data["frame_img"].copy()
        bbox = self.match_data.get("bbox")
        score = self.match_data["score"] * 100.0
        target_name = self.match_data.get("target_name", "TARGET")

        if bbox is not None and len(bbox) >= 4:
            draw = ImageDraw.Draw(frame_pil)
            x, y, w, h = [int(v) for v in bbox[:4]]

            draw.rectangle([x - 2, y - 2, x + w + 2, y + h + 2], outline="#000000", width=2)
            draw.rectangle([x, y, x + w, y + h], outline="#0078d4", width=5)

            tag_text = f" {target_name.upper()} ({score:.1f}%) "
            banner_h = 26
            top_y = max(0, y - banner_h)
            draw.rectangle([x, top_y, x + min(w, 280), y], fill="#0078d4")
            draw.text((x + 6, top_y + 4), tag_text, fill="#ffffff")

        return frame_pil

    def _update_modal_image(self):
        c_width = max(self.canvas_label.winfo_width(), 400)
        c_height = max(self.canvas_label.winfo_height(), 300)

        img_w, img_h = self.annotated_image.size
        aspect = img_w / img_h

        if c_width / c_height > aspect:
            target_h = c_height
            target_w = int(c_height * aspect)
        else:
            target_w = c_width
            target_h = int(c_width / aspect)

        target_w = max(target_w, 10)
        target_h = max(target_h, 10)

        resized_img = self.annotated_image.resize((target_w, target_h), Image.Resampling.LANCZOS)
        ctk_img = ctk.CTkImage(light_image=resized_img, dark_image=resized_img, size=(target_w, target_h))
        self.canvas_label.configure(image=ctk_img)

    def _save_frame(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            filetypes=[("JPEG Image", "*.jpg"), ("PNG Image", "*.png")],
            initialfile=f"match_frame_{self.match_data['frame_idx']}_{self.match_data['timestamp_str'].replace(':', '-')}.jpg"
        )
        if file_path:
            self.annotated_image.save(file_path)
            messagebox.showinfo("Saved Successfully", f"Match frame exported to:\n{file_path}")


class FaceSeekerApp(ctk.CTk):
    """
    Main Application Window built with Windows 11 Native Dark Styling and Multi-Target Support.
    """

    def __init__(self):
        super().__init__()

        self.title("🛡️ FACE SEEKER - Target Face Detector")
        self.geometry("1140x760")
        self.minsize(980, 680)
        self.configure(fg_color="#202020")

        # Multi-Target Subject Storage List
        # Format: [{'id': int, 'name': str, 'path': str, 'embedding': np.ndarray, 'crop_pil': PIL.Image, 'quality': str}]
        self.target_subjects = []
        self.video_path = None

        self.analysis_state = "IDLE"
        self.match_threshold = 0.36

        self.detected_matches = []
        self.msg_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()

        # Models
        self.face_detector = None
        self.face_recognizer = None
        self._init_ai_models()
        self._check_default_files()

        # Build UI layout
        self._build_header()
        self._build_input_section()
        self._build_action_bar()
        self._build_main_body()

        self.after(50, self._process_queue)

    def _init_ai_models(self):
        det_path = get_resource_path(os.path.join("models", "face_detection_yunet_2023mar.onnx"))
        rec_path = get_resource_path(os.path.join("models", "face_recognition_sface_2021dec.onnx"))

        if os.path.exists(det_path) and os.path.exists(rec_path):
            try:
                self.face_detector = cv2.FaceDetectorYN.create(det_path, "", (300, 300), 0.6, 0.3, 5000)
                self.face_recognizer = cv2.FaceRecognizerSF.create(rec_path, "")
            except Exception as e:
                print(f"Warning: Failed to load face models: {e}")

    def _check_default_files(self):
        default_target = "alia.jpg"
        if os.path.exists(default_target):
            self._add_target_subject(os.path.abspath(default_target), "Target #1 (Alia)")

        for f in os.listdir("."):
            if f.lower().endswith(".mp4"):
                self.video_path = os.path.abspath(f)
                break

    def _build_header(self):
        header_frame = ctk.CTkFrame(self, fg_color="#202020", corner_radius=0, height=56)
        header_frame.pack(fill="x", side="top")
        header_frame.pack_propagate(False)

        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=20, pady=10)

        lbl_app_title = ctk.CTkLabel(
            title_box,
            text="🛡️ FACE SEEKER",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="#ffffff"
        )
        lbl_app_title.pack(side="left")

        lbl_subtitle = ctk.CTkLabel(
            title_box,
            text="  |  Multi-Target Face Detector",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#adadad"
        )
        lbl_subtitle.pack(side="left")

        divider = ctk.CTkFrame(self, fg_color="#2d2d2d", height=1)
        divider.pack(fill="x", side="top")

    def _build_input_section(self):
        input_container = ctk.CTkFrame(self, fg_color="transparent")
        input_container.pack(fill="x", padx=20, pady=(15, 10))

        input_container.columnconfigure(0, weight=6)
        input_container.columnconfigure(1, weight=5)

        # LEFT: MULTI-TARGET SUBJECTS CONTAINER
        self.target_card = ctk.CTkFrame(input_container, fg_color="#2b2b2b", corner_radius=8, border_width=1, border_color="#3a3a3a")
        self.target_card.grid(row=0, column=0, padx=(0, 8), sticky="nsew")

        t_head_frame = ctk.CTkFrame(self.target_card, fg_color="transparent")
        t_head_frame.pack(fill="x", padx=14, pady=(10, 4))

        self.lbl_t_head = ctk.CTkLabel(
            t_head_frame,
            text=f"👤 Target Subjects ({len(self.target_subjects)} Loaded)",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#ffffff"
        )
        self.lbl_t_head.pack(side="left")

        btn_add_target = ctk.CTkButton(
            t_head_frame,
            text="➕ Add Target Subject",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#0078d4",
            hover_color="#005a9e",
            text_color="#ffffff",
            corner_radius=6,
            height=28,
            command=self._browse_and_add_target
        )
        btn_add_target.pack(side="right")

        # Scrollable row of Target Subject chips/avatars
        self.target_chips_frame = ctk.CTkScrollableFrame(self.target_card, fg_color="transparent", height=70, orientation="horizontal")
        self.target_chips_frame.pack(fill="x", padx=10, pady=(2, 8))

        self._render_target_chips()

        # RIGHT: VIDEO FILE SELECTION
        video_card = ctk.CTkFrame(input_container, fg_color="#2b2b2b", corner_radius=8, border_width=1, border_color="#3a3a3a")
        video_card.grid(row=0, column=1, padx=(8, 0), sticky="nsew")

        lbl_v_head = ctk.CTkLabel(
            video_card,
            text="📹 Video Source",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#ffffff"
        )
        lbl_v_head.pack(anchor="w", padx=14, pady=(10, 4))

        video_inner = ctk.CTkFrame(video_card, fg_color="transparent")
        video_inner.pack(fill="x", padx=14, pady=6)

        btn_pick_video = ctk.CTkButton(
            video_inner,
            text="🎥 Select Video File / Folder",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#3a3a3a",
            hover_color="#454545",
            text_color="#ffffff",
            border_width=1,
            border_color="#4d4d4d",
            corner_radius=6,
            height=32,
            command=self._select_video_file
        )
        btn_pick_video.pack(side="left", padx=(0, 12))

        self.video_meta_label = ctk.CTkLabel(
            video_inner,
            text="Metadata: No video selected",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#adadad",
            anchor="w"
        )
        self.video_meta_label.pack(side="left", fill="x", expand=True)

        if self.video_path:
            self._load_video_metadata(self.video_path)

    def _render_target_chips(self):
        """Render target subject cards inside target chips frame."""
        for child in self.target_chips_frame.winfo_children():
            child.destroy()

        if hasattr(self, 'lbl_t_head'):
            self.lbl_t_head.configure(text=f"👤 Target Subjects ({len(self.target_subjects)} Loaded)")

        if not self.target_subjects:
            lbl_empty = ctk.CTkLabel(self.target_chips_frame, text="No targets added. Click '➕ Add Target Subject'.", font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#adadad")
            lbl_empty.pack(padx=20, pady=15)
            return

        for idx, target in enumerate(self.target_subjects):
            chip = ctk.CTkFrame(self.target_chips_frame, fg_color="#1f1f1f", corner_radius=6, border_width=1, border_color="#383838")
            chip.pack(side="left", padx=5, pady=4)

            # Avatar image
            crop_pil = target.get("crop_pil")
            if crop_pil:
                crop_ctk = ctk.CTkImage(light_image=crop_pil, dark_image=crop_pil, size=(48, 48))
                lbl_img = ctk.CTkLabel(chip, image=crop_ctk, text="", corner_radius=4)
                lbl_img.pack(side="left", padx=6, pady=6)

            # Info labels
            info_box = ctk.CTkFrame(chip, fg_color="transparent")
            info_box.pack(side="left", padx=(0, 8), pady=4)

            lbl_name = ctk.CTkLabel(info_box, text=target["name"], font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#ffffff", anchor="w")
            lbl_name.pack(anchor="w")

            lbl_qual = ctk.CTkLabel(info_box, text=target["quality"], font=ctk.CTkFont(family="Segoe UI", size=10), text_color="#adadad", anchor="w")
            lbl_qual.pack(anchor="w")

            # Remove button
            btn_del = ctk.CTkButton(
                chip,
                text="✖",
                width=24,
                height=24,
                font=ctk.CTkFont(size=10, weight="bold"),
                fg_color="#3a3a3a",
                hover_color="#c42b1c",
                corner_radius=4,
                command=lambda t_id=target["id"]: self._remove_target_subject(t_id)
            )
            btn_del.pack(side="right", padx=(0, 6))

    def _browse_and_add_target(self):
        file_path = filedialog.askopenfilename(
            title="Select Target Subject Image",
            filetypes=[("Image Files", "*.jpg *.jpeg *.png *.bmp *.webp")]
        )
        if file_path:
            name = f"Target #{len(self.target_subjects) + 1}"
            self._add_target_subject(file_path, name)

    def _add_target_subject(self, path: str, name: str = None):
        if not os.path.exists(path):
            return

        img_bgr = cv2.imread(path)
        if img_bgr is None:
            messagebox.showerror("Image Error", f"Could not decode image at {path}")
            return

        h, w, _ = img_bgr.shape
        if name is None:
            name = f"Target #{len(self.target_subjects) + 1}"

        det_path = get_resource_path(os.path.join("models", "face_detection_yunet_2023mar.onnx"))
        rec_path = get_resource_path(os.path.join("models", "face_recognition_sface_2021dec.onnx"))

        embedding = None
        crop_pil = None
        qual_str = "Verified"

        if os.path.exists(det_path) and os.path.exists(rec_path):
            try:
                detector = cv2.FaceDetectorYN.create(det_path, "", (w, h), 0.5, 0.3, 5000)
                recognizer = cv2.FaceRecognizerSF.create(rec_path, "")

                _, faces = detector.detect(img_bgr)
                if faces is not None and len(faces) > 0:
                    aligned = recognizer.alignCrop(img_bgr, faces[0])
                    embedding = recognizer.feature(aligned)

                    crop_rgb = cv2.cvtColor(aligned, cv2.COLOR_BGR2RGB)
                    crop_pil = Image.fromarray(crop_rgb)

                    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
                    lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()

                    if lap_var > 150:
                        qual_str = "🟢 High Quality"
                    elif lap_var > 50:
                        qual_str = "🟡 Acceptable"
                    else:
                        qual_str = "⚠️ Blurry Image"
                else:
                    rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
                    crop_pil = Image.fromarray(rgb).resize((48, 48))
                    qual_str = "⚠️ No Face Detected"
            except Exception as e:
                qual_str = "Error"
        else:
            embedding = np.ones((1, 128), dtype=np.float32)
            rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            crop_pil = Image.fromarray(rgb).resize((48, 48))
            qual_str = "Offline Mode"

        target_obj = {
            "id": len(self.target_subjects) + 1,
            "name": name,
            "path": path,
            "embedding": embedding,
            "crop_pil": crop_pil,
            "quality": qual_str
        }
        self.target_subjects.append(target_obj)
        self._render_target_chips()

    def _remove_target_subject(self, target_id: int):
        self.target_subjects = [t for t in self.target_subjects if t["id"] != target_id]
        self._render_target_chips()

    def _build_action_bar(self):
        self.action_bar_container = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=8, border_width=1, border_color="#3a3a3a", height=60)
        self.action_bar_container.pack(fill="x", padx=20, pady=(0, 10))
        self.action_bar_container.pack_propagate(False)

        self.btn_holder = ctk.CTkFrame(self.action_bar_container, fg_color="transparent")
        self.btn_holder.pack(expand=True, fill="both", padx=15, pady=8)

        self._render_action_buttons()

    def _render_action_buttons(self):
        for child in self.btn_holder.winfo_children():
            child.destroy()

        if self.analysis_state in ["IDLE", "TERMINATED", "COMPLETED"]:
            btn_start = ctk.CTkButton(
                self.btn_holder,
                text="🚀  Start Analysis",
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                fg_color="#0078d4",
                hover_color="#005a9e",
                corner_radius=6,
                height=40,
                command=self._start_analysis
            )
            btn_start.pack(expand=True, fill="x", padx=100)

        elif self.analysis_state == "RUNNING":
            btn_pause = ctk.CTkButton(
                self.btn_holder,
                text="⏸️  Pause Analysis",
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                fg_color="#d13438",
                hover_color="#a8282b",
                corner_radius=6,
                height=40,
                command=self._pause_analysis
            )
            btn_pause.pack(expand=True, fill="x", padx=100)

        elif self.analysis_state == "PAUSED":
            self.btn_holder.columnconfigure(0, weight=1)
            self.btn_holder.columnconfigure(1, weight=1)

            btn_resume = ctk.CTkButton(
                self.btn_holder,
                text="▶️  Resume Analysis",
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                fg_color="#107c41",
                hover_color="#0c5d31",
                corner_radius=6,
                height=40,
                command=self._resume_analysis
            )
            btn_resume.grid(row=0, column=0, padx=(40, 10), sticky="ew")

            btn_terminate = ctk.CTkButton(
                self.btn_holder,
                text="🛑  Terminate Analysis",
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                fg_color="#c42b1c",
                hover_color="#9e2217",
                corner_radius=6,
                height=40,
                command=self._terminate_analysis
            )
            btn_terminate.grid(row=0, column=1, padx=(10, 40), sticky="ew")

    def _build_main_body(self):
        body_frame = ctk.CTkFrame(self, fg_color="transparent")
        body_frame.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        body_frame.columnconfigure(0, weight=5)
        body_frame.columnconfigure(1, weight=5)
        body_frame.rowconfigure(0, weight=1)

        # LEFT PANE: LIVE VIDEO PREVIEW
        preview_pane = ctk.CTkFrame(body_frame, fg_color="#2b2b2b", corner_radius=8, border_width=1, border_color="#3a3a3a")
        preview_pane.grid(row=0, column=0, padx=(0, 8), sticky="nsew")

        preview_header = ctk.CTkFrame(preview_pane, fg_color="transparent")
        preview_header.pack(fill="x", padx=15, pady=(12, 6))

        lbl_p_title = ctk.CTkLabel(
            preview_header,
            text="📺 Live Video Stream",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#ffffff"
        )
        lbl_p_title.pack(side="left")

        self.lbl_status_pill = ctk.CTkLabel(
            preview_header,
            text="  READY  ",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#383838",
            text_color="#ffffff",
            corner_radius=4
        )
        self.lbl_status_pill.pack(side="right")

        self.video_display_frame = ctk.CTkFrame(preview_pane, fg_color="#000000", corner_radius=6, width=220, height=165, border_width=1, border_color="#383838")
        self.video_display_frame.pack(side="top", pady=(6, 2))
        self.video_display_frame.pack_propagate(False)

        self.video_label = ctk.CTkLabel(self.video_display_frame, text="[ Live Video Feed ]", text_color="#64748b", width=220, height=165)
        self.video_label.pack(fill="both", expand=True)

        self.timeline_frame = ctk.CTkFrame(preview_pane, fg_color="#1a1a1a", corner_radius=4, height=20, border_width=1, border_color="#383838")
        self.timeline_frame.pack(fill="x", padx=15, pady=(2, 6))

        self.timeline_canvas = ctk.CTkCanvas(self.timeline_frame, bg="#1a1a1a", highlightthickness=0, height=18)
        self.timeline_canvas.pack(fill="both", expand=True)
        self.timeline_canvas.bind("<Button-1>", self._on_timeline_click)

        ctrl_bar = ctk.CTkFrame(preview_pane, fg_color="#1f1f1f", corner_radius=6, border_width=1, border_color="#383838")
        ctrl_bar.pack(fill="x", padx=15, pady=(2, 12), side="top")

        self.progress_bar = ctk.CTkProgressBar(ctrl_bar, fg_color="#383838", progress_color="#0078d4", height=8)
        self.progress_bar.set(0.0)
        self.progress_bar.pack(fill="x", padx=15, pady=(10, 6))

        stats_row = ctk.CTkFrame(ctrl_bar, fg_color="transparent")
        stats_row.pack(fill="x", padx=15, pady=(0, 6))

        self.lbl_time = ctk.CTkLabel(
            stats_row,
            text="⏱️ 00:00:00 / 00:00:00",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#ffffff"
        )
        self.lbl_time.pack(side="left", padx=(0, 12))

        self.lbl_fps = ctk.CTkLabel(
            stats_row,
            text="⚡ 0.0 FPS",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#adadad"
        )
        self.lbl_fps.pack(side="left", padx=(0, 12))

        self.lbl_eta = ctk.CTkLabel(
            stats_row,
            text="⏳ ETA: --:--",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#adadad"
        )
        self.lbl_eta.pack(side="left", padx=(0, 12))

        self.lbl_match_count_pill = ctk.CTkLabel(
            stats_row,
            text="  🎯 Matches: 0  ",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#0078d4",
            text_color="#ffffff",
            corner_radius=4
        )
        self.lbl_match_count_pill.pack(side="right")

        thresh_row = ctk.CTkFrame(ctrl_bar, fg_color="transparent")
        thresh_row.pack(fill="x", padx=15, pady=(0, 8))

        self.lbl_thresh_title = ctk.CTkLabel(
            thresh_row,
            text=f"Target Match Threshold: {self.match_threshold * 100:.0f}%",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#ffffff"
        )
        self.lbl_thresh_title.pack(side="left", padx=(0, 10))

        self.thresh_slider = ctk.CTkSlider(
            thresh_row,
            from_=0.20,
            to=0.80,
            number_of_steps=60,
            fg_color="#383838",
            progress_color="#0078d4",
            button_color="#0078d4",
            button_hover_color="#005a9e",
            command=self._on_threshold_change
        )
        self.thresh_slider.set(self.match_threshold)
        self.thresh_slider.pack(side="left", fill="x", expand=True)

        # RIGHT PANE: DETECTED MATCHES GALLERY
        gallery_pane = ctk.CTkFrame(body_frame, fg_color="#2b2b2b", corner_radius=8, border_width=1, border_color="#3a3a3a")
        gallery_pane.grid(row=0, column=1, padx=(8, 0), sticky="nsew")

        gallery_header = ctk.CTkFrame(gallery_pane, fg_color="transparent")
        gallery_header.pack(fill="x", padx=15, pady=(12, 8))

        lbl_g_title = ctk.CTkLabel(
            gallery_header,
            text="🎯 Detected Matches Gallery",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#ffffff"
        )
        lbl_g_title.pack(side="left")

        btn_box = ctk.CTkFrame(gallery_header, fg_color="transparent")
        btn_box.pack(side="right")

        btn_export_pdf = ctk.CTkButton(
            btn_box,
            text="📄 Export PDF Report",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#0078d4",
            hover_color="#005a9e",
            text_color="#ffffff",
            corner_radius=4,
            height=28,
            width=120,
            command=self._export_matches_pdf
        )
        btn_export_pdf.pack(side="left", padx=(0, 6))

        btn_export_csv = ctk.CTkButton(
            btn_box,
            text="📥 CSV",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color="#3a3a3a",
            hover_color="#454545",
            text_color="#ffffff",
            border_width=1,
            border_color="#4d4d4d",
            corner_radius=4,
            height=28,
            width=60,
            command=self._export_matches_csv
        )
        btn_export_csv.pack(side="left")

        self.match_scroll_frame = ctk.CTkScrollableFrame(
            gallery_pane,
            fg_color="#202020",
            corner_radius=6,
            label_text=""
        )
        self.match_scroll_frame.pack(fill="both", expand=True, padx=15, pady=(0, 12))

        self.empty_matches_label = ctk.CTkLabel(
            self.match_scroll_frame,
            text="No target matches detected yet.\nSelect target subjects & video then click 'Start Analysis'.",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#adadad"
        )
        self.empty_matches_label.pack(pady=50)

    # -------------------------------------------------------------------------
    # USER ACTION HANDLERS
    # -------------------------------------------------------------------------

    def _select_video_file(self):
        choice = messagebox.askyesnocancel("Video Source Selection", "Click 'YES' to select a Single Video File.\nClick 'NO' to select a Folder of Video Files for Batch Scanning.")
        if choice is True:
            file_path = filedialog.askopenfilename(
                title="Select Video File",
                filetypes=[("Video Files", "*.mp4 *.avi *.mkv *.mov *.m4v *.wmv")]
            )
            if file_path:
                self._load_video_metadata(file_path)
        elif choice is False:
            folder_path = filedialog.askdirectory(title="Select Folder of Video Files")
            if folder_path and os.path.exists(folder_path):
                v_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith(('.mp4', '.avi', '.mkv', '.mov', '.m4v'))]
                if v_files:
                    self.video_path = v_files[0]
                    self.video_meta_label.configure(text=f"📁 Batch Mode: {len(v_files)} Videos Found in Folder\nFirst: {os.path.basename(v_files[0])}", text_color="#0078d4")
                    self._reset_timeline_canvas()
                else:
                    messagebox.showwarning("No Videos Found", "No supported video files (.mp4, .avi, .mkv) found in selected directory.")

    def _load_video_metadata(self, path):
        if not os.path.exists(path):
            return

        self.video_path = path
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            self.video_meta_label.configure(text="Metadata: Invalid Video File", text_color="#ef4444")
            return

        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        fps = fps if fps > 0 else 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_sec = int(total_frames / fps) if fps > 0 else 0
        cap.release()

        dur_str = str(timedelta(seconds=duration_sec))
        fname = os.path.basename(path)
        if len(fname) > 20:
            fname = fname[:17] + "..."

        meta_str = f"File: {fname}\nRes: {w}x{h} | FPS: {fps:.1f} | Dur: {dur_str} ({total_frames} frames)"
        self.video_meta_label.configure(text=meta_str, text_color="#ffffff")
        self._reset_timeline_canvas()

    def _on_threshold_change(self, val):
        self.match_threshold = float(val)
        self.lbl_thresh_title.configure(text=f"Target Match Threshold: {self.match_threshold * 100:.0f}%")

    def _reset_timeline_canvas(self):
        self.timeline_canvas.delete("all")
        self.timeline_canvas.create_rectangle(0, 0, 1000, 20, fill="#1a1a1a", outline="")

    def _draw_match_on_timeline(self, progress):
        c_width = self.timeline_canvas.winfo_width()
        c_width = c_width if c_width > 50 else 300
        x = int(progress * c_width)
        self.timeline_canvas.create_line(x, 2, x, 16, fill="#0078d4", width=3)

    def _on_timeline_click(self, event):
        if not self.detected_matches or not self.video_path:
            return
        c_width = self.timeline_canvas.winfo_width()
        c_width = c_width if c_width > 50 else 300
        click_ratio = event.x / c_width

        closest_match = min(self.detected_matches, key=lambda m: abs(m.get('progress', 0.0) - click_ratio))
        if closest_match:
            MatchPreviewModal(self, closest_match)

    def _start_analysis(self):
        if not self.video_path or not os.path.exists(self.video_path):
            messagebox.showwarning("Video Required", "Please select a valid video file first.")
            return

        valid_targets = [t for t in self.target_subjects if t.get("embedding") is not None]
        if not valid_targets:
            messagebox.showwarning("Target Required", "Please add at least one valid target subject image first.")
            return

        self.detected_matches.clear()
        for child in self.match_scroll_frame.winfo_children():
            child.destroy()

        self.empty_matches_label = ctk.CTkLabel(
            self.match_scroll_frame,
            text=f"📡 Scanning video stream for {len(valid_targets)} target subject(s)...",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#0078d4"
        )
        self.empty_matches_label.pack(pady=40)

        self.lbl_match_count_pill.configure(text="  🎯 Matches: 0  ")
        self.progress_bar.set(0.0)
        self._reset_timeline_canvas()

        self.analysis_state = "RUNNING"
        self.lbl_status_pill.configure(text="  ANALYZING  ", fg_color="#0078d4", text_color="#ffffff")
        self._render_action_buttons()

        self.stop_event.clear()
        self.pause_event.clear()

        self.worker_thread = threading.Thread(target=self._analysis_worker, daemon=True)
        self.worker_thread.start()

    def _pause_analysis(self):
        self.analysis_state = "PAUSED"
        self.pause_event.set()
        self.lbl_status_pill.configure(text="  PAUSED  ", fg_color="#d13438", text_color="#ffffff")
        self._render_action_buttons()

    def _resume_analysis(self):
        self.analysis_state = "RUNNING"
        self.pause_event.clear()
        self.lbl_status_pill.configure(text="  ANALYZING  ", fg_color="#0078d4", text_color="#ffffff")
        self._render_action_buttons()

    def _terminate_analysis(self):
        self.analysis_state = "TERMINATED"
        self.stop_event.set()
        self.pause_event.clear()
        self.lbl_status_pill.configure(text="  STOPPED  ", fg_color="#c42b1c", text_color="#ffffff")
        self._render_action_buttons()

        self.video_label.configure(image="", text="[ Feed Terminated ]")
        self.progress_bar.set(0.0)
        self.lbl_time.configure(text="⏱️ 00:00:00 / 00:00:00")
        self.lbl_fps.configure(text="⚡ 0.0 FPS")
        self.lbl_eta.configure(text="⏳ ETA: --:--")

    # -------------------------------------------------------------------------
    # BACKGROUND WORKER THREAD (MULTI-TARGET MATCHING)
    # -------------------------------------------------------------------------

    def _analysis_worker(self):
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            self.msg_queue.put(("ERROR", "Failed to open video file"))
            return

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        fps = fps if fps > 0 else 30.0

        start_time = time.time()
        processed_count = 0
        frame_idx = 0

        det_path = get_resource_path(os.path.join("models", "face_detection_yunet_2023mar.onnx"))
        rec_path = get_resource_path(os.path.join("models", "face_recognition_sface_2021dec.onnx"))

        thread_detector = None
        thread_recognizer = None
        if os.path.exists(det_path) and os.path.exists(rec_path):
            try:
                thread_detector = cv2.FaceDetectorYN.create(det_path, "", (300, 300), 0.5, 0.3, 5000)
                thread_recognizer = cv2.FaceRecognizerSF.create(rec_path, "")
            except Exception as e:
                print("Error initializing thread detector/recognizer:", e)

        # Collect target subjects with valid embeddings
        valid_targets = [t for t in self.target_subjects if t.get("embedding") is not None]

        frame_step = 2

        while cap.isOpened():
            if self.stop_event.is_set():
                break

            while self.pause_event.is_set():
                if self.stop_event.is_set():
                    break
                time.sleep(0.1)

            ret, frame = cap.read()
            if not ret or frame is None:
                break

            frame_idx += 1
            if frame_idx % frame_step != 0:
                continue

            processed_count += 1
            h, w, _ = frame.shape

            det_w, det_h = 640, 360
            scale_x, scale_y = w / det_w, h / det_h

            target_matched = False
            best_score = 0.0
            matched_target = None
            matched_bbox = None
            crop_pil = None

            if thread_detector is not None and thread_recognizer is not None and len(valid_targets) > 0:
                thread_detector.setInputSize((det_w, det_h))
                det_frame = cv2.resize(frame, (det_w, det_h))
                _, faces = thread_detector.detect(det_frame)

                if faces is not None:
                    for face in faces:
                        scaled_face = face.copy()
                        scaled_face[0] *= scale_x
                        scaled_face[1] *= scale_y
                        scaled_face[2] *= scale_x
                        scaled_face[3] *= scale_y
                        scaled_face[4] *= scale_x
                        scaled_face[5] *= scale_y
                        scaled_face[6] *= scale_x
                        scaled_face[7] *= scale_y
                        scaled_face[8] *= scale_x
                        scaled_face[9] *= scale_y
                        scaled_face[10] *= scale_x
                        scaled_face[11] *= scale_y
                        scaled_face[12] *= scale_x
                        scaled_face[13] *= scale_y

                        aligned = thread_recognizer.alignCrop(frame, scaled_face)
                        feat = thread_recognizer.feature(aligned)

                        # Match against ALL loaded target subjects!
                        for target in valid_targets:
                            score = float(thread_recognizer.match(target["embedding"], feat, cv2.FaceRecognizerSF_FR_COSINE))

                            if score >= self.match_threshold and score > best_score:
                                target_matched = True
                                best_score = score
                                matched_target = target
                                matched_bbox = [int(scaled_face[0]), int(scaled_face[1]), int(scaled_face[2]), int(scaled_face[3])]
                                crop_rgb = cv2.cvtColor(aligned, cv2.COLOR_BGR2RGB)
                                crop_pil = Image.fromarray(crop_rgb)

            preview_bgr = cv2.resize(frame, (320, 180))
            rgb_preview = cv2.cvtColor(preview_bgr, cv2.COLOR_BGR2RGB)
            frame_pil = Image.fromarray(rgb_preview)

            sec = int(frame_idx / fps)
            timestamp_str = str(timedelta(seconds=sec))
            if len(timestamp_str) == 7:
                timestamp_str = "0" + timestamp_str

            tot_sec = int(total_frames / fps)
            tot_str = str(timedelta(seconds=tot_sec))
            if len(tot_str) == 7:
                tot_str = "0" + tot_str

            elapsed = time.time() - start_time
            curr_fps = processed_count / elapsed if elapsed > 0 else 0.0
            remaining_frames = total_frames - frame_idx
            eta_sec = int((remaining_frames / frame_step) / curr_fps) if curr_fps > 0 else 0
            eta_str = str(timedelta(seconds=eta_sec))

            finish_dt = datetime.now() + timedelta(seconds=eta_sec)
            finish_time_str = finish_dt.strftime("%I:%M %p")

            progress = frame_idx / total_frames

            full_frame_pil = None
            if target_matched:
                full_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                full_frame_pil = Image.fromarray(full_rgb)

                if matched_bbox is not None:
                    bx, by, bw, bh = [max(0, int(v)) for v in matched_bbox[:4]]
                    crop_bgr = frame[by:by + bh, bx:bx + bw]
                    if crop_bgr.size > 0:
                        crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
                        crop_pil = Image.fromarray(crop_rgb)

            match_data = None
            if target_matched and full_frame_pil is not None and matched_target is not None:
                match_data = {
                    "timestamp_str": timestamp_str,
                    "frame_idx": frame_idx,
                    "score": best_score,
                    "target_name": matched_target["name"],
                    "target_crop_pil": matched_target["crop_pil"],
                    "frame_img": full_frame_pil,
                    "crop_img": crop_pil,
                    "bbox": matched_bbox,
                    "progress": progress,
                    "video_source": self.video_path
                }

            self.msg_queue.put((
                "FRAME_UPDATE",
                {
                    "frame_pil": frame_pil,
                    "progress": progress,
                    "timestamp_str": f"{timestamp_str} / {tot_str}",
                    "fps_str": f"{curr_fps:.1f} FPS",
                    "eta_str": f"ETA: {eta_str} • Finish at {finish_time_str}",
                    "match_data": match_data
                }
            ))

            time.sleep(0.015)

        cap.release()
        if not self.stop_event.is_set():
            self.msg_queue.put(("FINISHED", None))

    # -------------------------------------------------------------------------
    # GUI QUEUE DISPATCHER & MATCH CARD CREATION
    # -------------------------------------------------------------------------

    def _process_queue(self):
        try:
            while True:
                msg_type, payload = self.msg_queue.get_nowait()

                if msg_type == "FRAME_UPDATE":
                    self._update_live_video_image(payload["frame_pil"])
                    self.progress_bar.set(payload["progress"])
                    self.lbl_time.configure(text=f"⏱️ {payload['timestamp_str']}")
                    self.lbl_fps.configure(text=f"⚡ {payload['fps_str']}")
                    self.lbl_eta.configure(text=f"⏳ {payload['eta_str']}")

                    if payload["match_data"] is not None:
                        self._add_match_card(payload["match_data"])
                        self._draw_match_on_timeline(payload["match_data"]["progress"])

                elif msg_type == "FINISHED":
                    self.analysis_state = "COMPLETED"
                    self.lbl_status_pill.configure(text="  COMPLETED  ", fg_color="#107c41", text_color="#ffffff")
                    self._render_action_buttons()
                    messagebox.showinfo("Analysis Complete", f"Video Analysis completed!\nTotal Matches Found: {len(self.detected_matches)}")

                elif msg_type == "ERROR":
                    self.analysis_state = "TERMINATED"
                    self._render_action_buttons()
                    messagebox.showerror("Error", payload)

        except queue.Empty:
            pass

        self.after(40, self._process_queue)

    def _update_live_video_image(self, frame_pil):
        if self.analysis_state in ["TERMINATED", "IDLE"]:
            return
        target_w, target_h = 220, 165
        resized = frame_pil.resize((target_w, target_h), Image.Resampling.BILINEAR)
        ctk_img = ctk.CTkImage(light_image=resized, dark_image=resized, size=(target_w, target_h))
        self.video_label.configure(image=ctk_img, text="")

    def _add_match_card(self, match_data):
        if len(self.detected_matches) == 0:
            if hasattr(self, 'empty_matches_label') and self.empty_matches_label.winfo_exists():
                self.empty_matches_label.destroy()

        self.detected_matches.append(match_data)
        match_count = len(self.detected_matches)
        self.lbl_match_count_pill.configure(text=f"  🎯 Matches: {match_count}  ")

        card = ctk.CTkFrame(
            self.match_scroll_frame,
            fg_color="#252525",
            corner_radius=6,
            border_width=1,
            border_color="#383838"
        )
        card.pack(fill="x", padx=5, pady=6)

        def _on_hover(e):
            card.configure(fg_color="#2e2e2e", border_color="#0078d4")
        def _on_leave(e):
            card.configure(fg_color="#252525", border_color="#383838")

        card.bind("<Enter>", _on_hover)
        card.bind("<Leave>", _on_leave)

        card.columnconfigure(1, weight=1)

        crop_pil = match_data.get("crop_img")
        if crop_pil is None:
            crop_pil = Image.new("RGB", (70, 70), "#383838")

        crop_pil_sq = crop_pil.resize((68, 68), Image.Resampling.LANCZOS)
        crop_ctk = ctk.CTkImage(light_image=crop_pil_sq, dark_image=crop_pil_sq, size=(68, 68))

        lbl_crop = ctk.CTkLabel(card, image=crop_ctk, text="", corner_radius=4)
        lbl_crop.grid(row=0, column=0, rowspan=2, padx=10, pady=10)

        target_name = match_data.get("target_name", "Target Subject")
        lbl_time = ctk.CTkLabel(
            card,
            text=f"⏱️ {match_data['timestamp_str']}  •  🎯 {target_name}",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#ffffff",
            anchor="w"
        )
        lbl_time.grid(row=0, column=1, sticky="w", padx=5, pady=(10, 0))

        lbl_frame = ctk.CTkLabel(
            card,
            text=f"Frame #{match_data['frame_idx']}  •  Target Matched",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#adadad",
            anchor="w"
        )
        lbl_frame.grid(row=1, column=1, sticky="w", padx=5, pady=(0, 10))

        right_box = ctk.CTkFrame(card, fg_color="transparent")
        right_box.grid(row=0, column=2, rowspan=2, padx=10, pady=10)

        score_pct = match_data['score'] * 100.0
        badge_lbl = ctk.CTkLabel(
            right_box,
            text=f"{score_pct:.1f}% Match",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#0078d4",
            text_color="#ffffff",
            corner_radius=4,
            padx=8,
            pady=3
        )
        badge_lbl.pack(pady=(0, 6))

        btn_inspect = ctk.CTkButton(
            right_box,
            text="🔍 Details",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color="#3a3a3a",
            hover_color="#454545",
            text_color="#ffffff",
            border_width=1,
            border_color="#4d4d4d",
            height=26,
            width=75,
            corner_radius=4,
            command=lambda data=match_data: self._open_match_modal(data)
        )
        btn_inspect.pack()

        card.bind("<Button-1>", lambda e, data=match_data: self._open_match_modal(data))
        lbl_time.bind("<Button-1>", lambda e, data=match_data: self._open_match_modal(data))
        lbl_frame.bind("<Button-1>", lambda e, data=match_data: self._open_match_modal(data))
        lbl_crop.bind("<Button-1>", lambda e, data=match_data: self._open_match_modal(data))

    def _open_match_modal(self, match_data):
        MatchPreviewModal(self, match_data)

    def _export_matches_pdf(self):
        if not self.detected_matches:
            messagebox.showinfo("No Data", "There are no detected target matches to export.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Document", "*.pdf")],
            initialfile="face_seeker_incident_report.pdf"
        )

        if file_path:
            target_summary_path = self.target_subjects[0]["path"] if self.target_subjects else "N/A"
            success = generate_pdf_report(target_summary_path, self.video_path, self.detected_matches, file_path)
            if success:
                messagebox.showinfo("PDF Export Complete", f"Official Incident Report exported to:\n{file_path}")
            else:
                messagebox.showerror("Export Error", "Failed to generate PDF incident report.")

    def _export_matches_csv(self):
        if not self.detected_matches:
            messagebox.showinfo("No Data", "There are no detected target matches to export.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV File", "*.csv")],
            initialfile="face_seeker_match_report.csv"
        )

        if file_path:
            try:
                with open(file_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Match_ID", "Target_Name", "Timestamp_HHMMSS", "Frame_Number", "Similarity_Score_Pct", "Bounding_Box_XYWH", "Video_Source"])
                    for idx, match in enumerate(self.detected_matches, 1):
                        writer.writerow([
                            idx,
                            match.get("target_name", "Target Subject"),
                            match["timestamp_str"],
                            match["frame_idx"],
                            f"{match['score'] * 100.0:.2f}%",
                            str(match.get("bbox", [])),
                            os.path.basename(match.get("video_source", ""))
                        ])
                messagebox.showinfo("Export Successful", f"Match report successfully exported to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Export Failed", f"Could not write CSV file:\n{e}")
