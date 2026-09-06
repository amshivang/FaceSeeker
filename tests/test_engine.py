# ponytail: clean automated tests for engine components, video loop, socket IPC, and export logic
import os
import sys
import time
import json
import socket
import threading
import unittest
import numpy as np
import cv2

engine_sources = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "FaceSeeker.Engine", "BUILD_SOURCES"))
if engine_sources not in sys.path:
    sys.path.insert(0, engine_sources)

import config
from result_models import FaceMatch, ScanProgress, VideoComplete
from detector import FaceDetector
from recognizer import FaceRecognizer
from pipeline import FaceSearchPipeline
from video_scanner import VideoScanner
import server

class TestResultModels(unittest.TestCase):
    def test_face_match_creation(self):
        m = FaceMatch(
            target_name="Alice",
            video_path="test.mp4",
            frame_number=42,
            timestamp_str="00:00:01.400",
            confidence=0.88,
            thumbnail_b64="AAAA",
            bbox=[10, 10, 50, 50]
        )
        self.assertEqual(m.target_name, "Alice")
        self.assertEqual(m.confidence, 0.88)
        self.assertEqual(len(m.bbox), 4)

    def test_scan_progress(self):
        p = ScanProgress(video_path="test.mp4", frame_current=10, frame_total=100)
        self.assertEqual(p.frame_current, 10)
        self.assertEqual(p.frame_total, 100)

class TestModelsAndInference(unittest.TestCase):
    def test_config_models_exist(self):
        self.assertTrue(os.path.isfile(config.YUNET_MODEL), f"YuNet model not found: {config.YUNET_MODEL}")
        self.assertTrue(os.path.isfile(config.SFACE_MODEL), f"SFace model not found: {config.SFACE_MODEL}")

    def test_detector_empty_frame(self):
        det = FaceDetector()
        res = det.detect(None)
        self.assertEqual(res, [])
        blank = np.zeros((100, 100, 3), dtype=np.uint8)
        res2 = det.detect(blank)
        self.assertEqual(res2, [])

    def test_detector_downscaling_large_frame(self):
        det = FaceDetector()
        # 1. Verify blank 1280x720 frame runs through downscale branch without error and returns []
        large_blank = np.zeros((720, 1280, 3), dtype=np.uint8)
        res = det.detect(large_blank, max_dim=640)
        self.assertEqual(res, [])

        # 2. Mock internal detector to verify coordinate re-projection when faces are detected
        # Frame: 720x1280 (h=720, w=1280). Max dim is 1280, scale = 640 / 1280 = 0.5.
        # inv_scale = 1 / 0.5 = 2.0.
        mock_face = np.array([
            10.0, 20.0, 30.0, 40.0,        # bbox: x, y, w, h
            15.0, 25.0, 35.0, 25.0, 25.0,  # landmarks: re_x, re_y, le_x, le_y, nt_x
            35.0, 18.0, 45.0, 32.0, 45.0,  # nt_y, rc_x, rc_y, lc_x, lc_y
            0.95                           # confidence score
        ], dtype=np.float32)

        class MockDetectorYN:
            def __init__(self):
                self.input_size = None
            def setInputSize(self, size):
                self.input_size = size
            def detect(self, df):
                return None, [mock_face.copy()]

        det.detector = MockDetectorYN()

        scaled_faces = det.detect(large_blank, max_dim=640)
        self.assertEqual(len(scaled_faces), 1)
        sf = scaled_faces[0]

        # Verify input size was set to downscaled dimensions (640, 360)
        self.assertEqual(det.detector.input_size, (640, 360))

        # Verify bbox scaled back by 2.0 (inv_scale)
        np.testing.assert_allclose(sf[0:4], [20.0, 40.0, 60.0, 80.0])
        # Verify landmarks scaled back by 2.0
        np.testing.assert_allclose(sf[4:14], [30.0, 50.0, 70.0, 50.0, 50.0, 70.0, 36.0, 90.0, 64.0, 90.0])
        # Verify confidence score untouched
        self.assertAlmostEqual(float(sf[14]), 0.95, places=5)

    def test_recognizer_match_score(self):
        rec = FaceRecognizer()
        emb1 = np.ones((1, 128), dtype=np.float32)
        emb2 = np.ones((1, 128), dtype=np.float32)
        score = rec.match_score(emb1, emb2)
        self.assertIsInstance(score, float)
        self.assertTrue(rec.is_match(emb1, emb2))

    def test_pipeline_target_lifecycle(self):
        pipe = FaceSearchPipeline()
        self.assertFalse(pipe.has_targets())
        pipe.clear_targets()
        self.assertFalse(pipe.has_targets())

        # Test timestamp formatting
        ts = pipe._timestamp(3661.125)
        self.assertEqual(ts, "01:01:01.125")

        # Test thumbnail encoding
        crop = np.zeros((64, 64, 3), dtype=np.uint8)
        b64 = pipe._encode_thumbnail(crop)
        self.assertTrue(len(b64) > 0)

    def test_search_frame_best_match_winner(self):
        pipe = FaceSearchPipeline()
        dummy_det = np.array([10, 10, 50, 50, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.99], dtype=np.float32)
        pipe.detector.detect = lambda img: [dummy_det]

        pipe.recognizer.extract = lambda img, det: np.ones((1, 128), dtype=np.float32)
        pipe.recognizer.cosine_threshold = 0.363

        emb1 = np.zeros((1, 128), dtype=np.float32)
        emb2 = np.zeros((1, 128), dtype=np.float32)
        pipe.targets["TargetA"] = [emb1]
        pipe.targets["TargetB"] = [emb2]

        def mock_match_score(query_emb, target_emb):
            if target_emb is emb1:
                return 0.50  # above threshold 0.363
            elif target_emb is emb2:
                return 0.85  # higher score above threshold
            return 0.0

        pipe.recognizer.match_score = mock_match_score

        dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        matches = pipe.search_frame(dummy_frame, frame_num=1, fps=30.0, video_path="video.mp4")

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].target_name, "TargetB")
        self.assertEqual(matches[0].confidence, 0.85)

class TestVideoScanner(unittest.TestCase):
    def test_synthetic_video_scan(self):
        """Generates a synthetic MP4 test video and scans it to verify frame iteration and callbacks."""
        test_video_path = os.path.join(os.path.dirname(__file__), "synthetic_test.mp4")
        width, height = 320, 240
        fps = 10
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(test_video_path, fourcc, fps, (width, height))

        # Write 20 dummy frames
        for i in range(20):
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            cv2.circle(frame, (50 + i * 5, 100), 20, (200, 200, 200), -1)
            out.write(frame)
        out.release()

        pipe = FaceSearchPipeline()
        scanner = VideoScanner(pipe, frame_skip=2)

        progress_events = []
        def on_prog(v, cur, tot):
            progress_events.append((cur, tot))

        res = scanner.scan(test_video_path, on_progress_cb=on_prog)
        self.assertEqual(res.error, "")
        self.assertTrue(len(progress_events) > 0)

        # Cleanup
        if os.path.exists(test_video_path):
            os.remove(test_video_path)

class TestSocketServerIPC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_port = 55433
        cls.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cls.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        cls.server_sock.bind(("127.0.0.1", cls.test_port))
        cls.server_sock.listen(5)
        cls._running = True

        def run_srv():
            while getattr(cls, "_running", True):
                try:
                    conn, _ = cls.server_sock.accept()
                    server.handle_client(conn)
                except:
                    break

        cls.thread = threading.Thread(target=run_srv, daemon=True)
        cls.thread.start()
        time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        cls._running = False
        try:
            cls.server_sock.close()
        except:
            pass

    def test_ping_pong_and_registration(self):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", self.test_port))
        f = client.makefile("r", encoding="utf-8")

        # Send ping
        cmd = json.dumps({"cmd": "ping"}) + "\n"
        client.sendall(cmd.encode("utf-8"))

        resp = f.readline()
        data = json.loads(resp)
        self.assertEqual(data.get("type"), "pong")

        # Send invalid register_target to verify register_result payload format
        cmd_reg = json.dumps({"cmd": "register_target", "name": "InvalidTest", "image_b64": "invalid_base64_data"}) + "\n"
        client.sendall(cmd_reg.encode("utf-8"))
        resp_reg = f.readline()
        data_reg = json.loads(resp_reg)
        self.assertEqual(data_reg.get("type"), "register_result")
        self.assertFalse(data_reg.get("success"))

        # Send clear_targets
        cmd = json.dumps({"cmd": "clear_targets"}) + "\n"
        client.sendall(cmd.encode("utf-8"))
        resp2 = f.readline()
        data2 = json.loads(resp2)
        self.assertEqual(data2.get("type"), "cleared")

        # Test cancel responsiveness
        cmd_cancel = json.dumps({"cmd": "cancel"}) + "\n"
        client.sendall(cmd_cancel.encode("utf-8"))
        resp3 = f.readline()
        data3 = json.loads(resp3)
        self.assertEqual(data3.get("type"), "cancelled")

        client.close()

    def test_scan_concurrency_rejection(self):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", self.test_port))
        f = client.makefile("r", encoding="utf-8")

        scan_started = threading.Event()
        scan_proceed = threading.Event()

        orig_scanner = server.VideoScanner
        class SlowScanner:
            def __init__(self, *args, **kwargs):
                pass
            def scan(self, *args, **kwargs):
                scan_started.set()
                scan_proceed.wait(timeout=5)
                return VideoComplete(video_path="test.mp4", total_matches=0)

        server.VideoScanner = SlowScanner
        try:
            # Start first scan
            cmd1 = json.dumps({"cmd": "scan", "videos": ["test.mp4"]}) + "\n"
            client.sendall(cmd1.encode("utf-8"))

            self.assertTrue(scan_started.wait(timeout=2))

            # Send second scan command while first is running
            cmd2 = json.dumps({"cmd": "scan", "videos": ["test.mp4"]}) + "\n"
            client.sendall(cmd2.encode("utf-8"))

            resp = f.readline()
            data = json.loads(resp)
            self.assertEqual(data.get("type"), "error")
            self.assertIn("already in progress", data.get("message", ""))
        finally:
            scan_proceed.set()
            server.VideoScanner = orig_scanner
            client.close()

if __name__ == "__main__":
    unittest.main()