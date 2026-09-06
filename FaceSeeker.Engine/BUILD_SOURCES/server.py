# ponytail: clean socket server entrypoint, stdlib only (socket, json, base64, threading)
# FIX: BUG-01 — scan runs in a background thread so cancel commands are processed immediately
# FIX: BUG-12 — threading.Event for cancel_flag, thread-safe send_json with lock
import os
import sys
import json
import socket
import base64
import threading
import cv2
import numpy as np

# Ensure current directory is on sys.path
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

try:
    import config
    from pipeline import FaceSearchPipeline
    from video_scanner import VideoScanner
except ImportError:
    from . import config
    from .pipeline import FaceSearchPipeline
    from .video_scanner import VideoScanner

pipeline = FaceSearchPipeline()
cancel_event = threading.Event()
_send_lock = threading.Lock()  # serialize socket writes from scan thread and main thread
_scan_thread = None  # track active scan thread

def send_json(conn, data):
    payload = json.dumps(data) + "\n"
    with _send_lock:
        try:
            conn.sendall(payload.encode("utf-8"))
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass  # client disconnected

def handle_ping(conn):
    send_json(conn, {"type": "pong"})

def handle_register_target(conn, msg):
    try:
        raw_b64 = msg.get("image_b64", "")
        img_bytes = base64.b64decode(raw_b64)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            send_json(conn, {"type": "register_result", "name": msg.get("name", ""), "success": False, "error": "Invalid image data"})
            return
        success = pipeline.register_target(msg.get("name", ""), img)
        send_json(conn, {"type": "register_result", "name": msg.get("name", ""), "success": bool(success)})
    except Exception as e:
        send_json(conn, {"type": "register_result", "name": msg.get("name", ""), "success": False, "error": str(e)})

def handle_clear_targets(conn):
    pipeline.clear_targets()
    send_json(conn, {"type": "cleared"})

def _scan_worker(conn, msg):
    """Runs in a background thread so the main socket loop can still process cancel."""
    try:
        cancel_event.clear()
        cosine_threshold = float(msg.get("cosine_threshold", config.COSINE_THRESHOLD))
        pipeline.recognizer.cosine_threshold = cosine_threshold
        frame_skip = int(msg.get("frame_skip", config.FRAME_SKIP))
        scanner = VideoScanner(pipeline, frame_skip=frame_skip)

        # Wrap cancel_event as a list-like interface for backward compat with VideoScanner
        cancel_flag_adapter = type('', (), {'__getitem__': lambda s, i: cancel_event.is_set()})()

        def on_match(match):
            send_json(conn, {
                "type": "match",
                "target_name": match.target_name,
                "video_path": match.video_path,
                "frame_number": match.frame_number,
                "timestamp_str": match.timestamp_str,
                "confidence": match.confidence,
                "thumbnail_b64": match.thumbnail_b64,
                "bbox": match.bbox
            })

        def on_progress(video_path, current, total):
            send_json(conn, {
                "type": "progress",
                "video_path": video_path,
                "frame_current": current,
                "frame_total": total
            })

        # SEC-07: validate video paths have allowed extensions
        allowed_exts = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.ts'}
        videos = msg.get("videos", [])
        for v in videos:
            if cancel_event.is_set():
                break
            ext = os.path.splitext(v)[1].lower()
            if ext not in allowed_exts:
                send_json(conn, {
                    "type": "video_done",
                    "video_path": v,
                    "total_matches": 0,
                    "error": f"Rejected: unsupported file extension '{ext}'"
                })
                continue
            res = scanner.scan(v, on_match_cb=on_match, on_progress_cb=on_progress, cancel_flag=cancel_flag_adapter)
            send_json(conn, {
                "type": "video_done",
                "video_path": res.video_path,
                "total_matches": res.total_matches,
                "error": res.error
            })

        if cancel_event.is_set():
            send_json(conn, {"type": "cancelled"})
        else:
            send_json(conn, {"type": "scan_complete"})
    except Exception as e:
        send_json(conn, {"type": "error", "message": f"Scan failed: {e}"})

def handle_scan(conn, msg):
    global _scan_thread
    if _scan_thread is not None and _scan_thread.is_alive():
        send_json(conn, {"type": "error", "message": "A scan is already in progress"})
        return
    _scan_thread = threading.Thread(target=_scan_worker, args=(conn, msg), daemon=True)
    _scan_thread.start()

def handle_cancel(conn):
    cancel_event.set()
    send_json(conn, {"type": "cancelled"})

def handle_client(conn):
    f = conn.makefile("r", encoding="utf-8")
    try:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except Exception as parse_err:
                send_json(conn, {"type": "error", "message": f"Malformed JSON: {parse_err}"})
                continue

            cmd = msg.get("cmd")
            try:
                if cmd == "ping":
                    handle_ping(conn)
                elif cmd == "register_target":
                    handle_register_target(conn, msg)
                elif cmd == "clear_targets":
                    handle_clear_targets(conn)
                elif cmd == "scan":
                    handle_scan(conn, msg)
                elif cmd == "cancel":
                    handle_cancel(conn)
                else:
                    send_json(conn, {"type": "error", "message": f"Unknown cmd: {cmd}"})
            except Exception as cmd_err:
                send_json(conn, {"type": "error", "message": f"Command '{cmd}' failed: {cmd_err}"})
    finally:
        # Wait for scan thread to finish before closing socket
        if _scan_thread and _scan_thread.is_alive():
            cancel_event.set()
            _scan_thread.join(timeout=5)
        f.close()
        conn.close()

def main():
    host = config.SERVER_HOST
    port = config.SERVER_PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((host, port))
    server_sock.listen(1)
    print(f"FaceSeeker Engine listening on {host}:{port}", flush=True)

    try:
        while True:
            try:
                conn, _ = server_sock.accept()
                handle_client(conn)
            except (ConnectionResetError, BrokenPipeError):
                continue
    except KeyboardInterrupt:
        pass
    finally:
        server_sock.close()

if __name__ == "__main__":
    main()