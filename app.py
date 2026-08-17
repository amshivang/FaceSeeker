import os
import csv
import io
import time
import cv2
import json
import queue
import threading
from typing import Optional
import webview
from flask import Flask, render_template, request, jsonify, Response, stream_with_context, send_file, send_from_directory
from face_engine import FaceEngine

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

VALID_VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov'}

# Global engine instance
engine = FaceEngine()

# Queues for web streaming
frame_queue = queue.Queue(maxsize=2)
sse_queue = queue.Queue(maxsize=100)

# Tracks the video currently loaded/streamed for the Review timeline player,
# and the matches found during the current session (used for CSV export).
current_video_path: dict[str, Optional[str]] = {"path": None}
session_matches: list[dict] = []


def _cleanup_uploads():
    """
    Remove leftover suspect/match crop images from previous sessions.
    Sensitive imagery should not silently persist on disk between runs.
    """
    folder = app.config['UPLOAD_FOLDER']
    try:
        for fname in os.listdir(folder):
            if fname.startswith('match_') or fname.startswith('target_'):
                try:
                    os.remove(os.path.join(folder, fname))
                except OSError:
                    pass
    except OSError:
        pass


_cleanup_uploads()


def notify_sse(event_type, data):
    try:
        if sse_queue.full():
            sse_queue.get_nowait()
        sse_queue.put_nowait((event_type, data))
    except queue.Full:
        pass


# Setup Callbacks
def on_frame_update(frame, stats):
    # Send frame to MJPEG stream
    try:
        # Encode frame to JPEG
        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if ret:
            if frame_queue.full():
                frame_queue.get_nowait()
            frame_queue.put_nowait(buffer.tobytes())
    except queue.Full:
        pass

    # Send stats to SSE
    stats_dict = {
        "frame_index": stats.frame_index,
        "total_frames": stats.total_frames,
        "processed_frames": stats.processed_frames,
        "fps": stats.fps,
        "elapsed_time": stats.elapsed_time,
        "eta": stats.eta,
        "progress_percent": stats.progress_percent,
        "detected_faces_count": stats.detected_faces_count,
        "matches_count": stats.matches_count
    }
    notify_sse("stats", stats_dict)

def on_match_found(match):
    # Save face crop temporarily to serve it
    match_filename = f"match_{match.frame_index}_{match.target_id}.jpg"
    match_path = os.path.join(app.config['UPLOAD_FOLDER'], match_filename)
    cv2.imwrite(match_path, match.face_crop)

    video_path = current_video_path.get("path") or ""
    match_dict = {
        "frame_index": match.frame_index,
        "timestamp": match.timestamp,
        "timestamp_str": match.timestamp_str,
        "similarity": match.similarity,
        "score": match.score,
        "target_id": match.target_id,
        "target_name": match.target_name,
        "image_url": f"/uploads/{match_filename}",
        "video_name": os.path.basename(video_path)
    }
    session_matches.append({**match_dict, "video_path": video_path})
    notify_sse("match", match_dict)

def on_status_change(state):
    notify_sse("status", {"state": state.value})

def on_complete(summary):
    notify_sse("complete", summary)

engine.on_frame_update = on_frame_update
engine.on_match_found = on_match_found
engine.on_status_change = on_status_change
engine.on_complete = on_complete


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/select_target', methods=['POST'])
def select_target():
    window = webview.windows[0] if webview.windows else None
    if not window:
        return jsonify({"success": False, "message": "No active window found."})

    result = window.create_file_dialog(
        webview.OPEN_DIALOG,
        allow_multiple=True,
        file_types=('Image Files (*.jpg;*.jpeg;*.png;*.bmp)', 'All Files (*.*)')
    )

    if not result or len(result) == 0:
        return jsonify({"success": False, "message": "No file selected"})

    added = []
    errors = []
    for file_path in result:
        res = engine.add_target(file_path)
        if res.success:
            thumb_filename = f"target_{res.target_id}.jpg"
            thumb_path = os.path.join(app.config['UPLOAD_FOLDER'], thumb_filename)
            cv2.imwrite(thumb_path, res.crop)
            added.append({
                "target_id": res.target_id,
                "name": res.name,
                "thumbnail_url": f"/uploads/{thumb_filename}",
                "sharpness": res.sharpness,
                "is_blurry": res.is_blurry,
                "message": res.message
            })
        else:
            errors.append({"file": os.path.basename(file_path), "message": res.message})

    return jsonify({"success": len(added) > 0, "targets": added, "errors": errors})

@app.route('/api/remove_target', methods=['POST'])
def remove_target():
    data = request.json or {}
    target_id = data.get('target_id')
    if not target_id:
        return jsonify({"success": False, "message": "target_id required"})

    ok = engine.remove_target(target_id)

    thumb_path = os.path.join(app.config['UPLOAD_FOLDER'], f"target_{target_id}.jpg")
    if os.path.exists(thumb_path):
        try:
            os.remove(thumb_path)
        except OSError:
            pass

    return jsonify({"success": ok})

@app.route('/api/list_targets')
def list_targets():
    targets = [{
        "target_id": t.id,
        "name": t.name,
        "thumbnail_url": f"/uploads/target_{t.id}.jpg",
        "sharpness": t.sharpness,
        "is_blurry": t.is_blurry
    } for t in engine.list_targets()]
    return jsonify({"success": True, "targets": targets})

@app.route('/api/select_video', methods=['POST'])
def select_video():
    window = webview.windows[0] if webview.windows else None
    if not window:
        return jsonify({"success": False, "message": "No active window found."})

    result = window.create_file_dialog(
        webview.OPEN_DIALOG,
        allow_multiple=False,
        file_types=('Video Files (*.mp4;*.avi;*.mkv;*.mov)', 'All Files (*.*)')
    )

    if not result or len(result) == 0:
        return jsonify({"success": False, "message": "No file selected"})

    file_path = result[0]
    info = engine.load_video(file_path)
    if info:
        current_video_path["path"] = file_path
        return jsonify({
            "success": True,
            "path": file_path,
            "fps": info.fps,
            "total_frames": info.total_frames,
            "duration": info.duration,
            "resolution": f"{info.width}x{info.height}"
        })
    else:
        return jsonify({"success": False, "message": "Failed to load video metadata."})

@app.route('/api/select_video_folder', methods=['POST'])
def select_video_folder():
    window = webview.windows[0] if webview.windows else None
    if not window:
        return jsonify({"success": False, "message": "No active window found."})

    result = window.create_file_dialog(webview.FOLDER_DIALOG)
    if not result or len(result) == 0:
        return jsonify({"success": False, "message": "No folder selected"})

    folder_path = result[0]
    videos = []
    try:
        for entry in sorted(os.listdir(folder_path)):
            full_path = os.path.join(folder_path, entry)
            if os.path.isfile(full_path) and os.path.splitext(entry)[1].lower() in VALID_VIDEO_EXTENSIONS:
                videos.append(full_path)
    except OSError as e:
        return jsonify({"success": False, "message": str(e)})

    if not videos:
        return jsonify({"success": False, "message": "No supported video files found in that folder."})

    return jsonify({"success": True, "folder": folder_path, "videos": videos})

@app.route('/api/video_info', methods=['POST'])
def video_info():
    """Load metadata for a known file path (used to advance the batch queue)."""
    data = request.json or {}
    video_path = data.get('path')
    if not video_path:
        return jsonify({"success": False, "message": "path required"})

    info = engine.load_video(video_path)
    if info:
        current_video_path["path"] = video_path
        return jsonify({
            "success": True,
            "path": video_path,
            "fps": info.fps,
            "total_frames": info.total_frames,
            "duration": info.duration,
            "resolution": f"{info.width}x{info.height}"
        })
    return jsonify({"success": False, "message": f"Failed to load video metadata: {video_path}"})

@app.route('/api/action', methods=['POST'])
def action():
    data = request.json
    cmd = data.get('command')

    if cmd == 'start':
        video_path = data.get('video_path')
        if not video_path:
            return jsonify({"success": False, "message": "No video selected"})
        try:
            current_video_path["path"] = video_path
            success = engine.start(video_path)
            return jsonify({"success": success})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)})

    elif cmd == 'pause':
        return jsonify({"success": engine.pause()})
    elif cmd == 'resume':
        return jsonify({"success": engine.resume()})
    elif cmd == 'terminate':
        return jsonify({"success": engine.terminate()})

    return jsonify({"success": False, "message": "Unknown command"})

@app.route('/api/thresholds', methods=['POST'])
def set_thresholds():
    data = request.json or {}
    cosine = data.get('cosine')
    frame_skip = data.get('frame_skip')
    if cosine is not None:
        engine.set_thresholds(cosine_threshold=float(cosine))
    if frame_skip is not None:
        engine.set_performance(frame_skip=int(frame_skip))
    return jsonify({"success": True})

@app.route('/api/engine_info')
def engine_info():
    return jsonify({
        "success": True,
        "gpu_accelerated": engine.gpu_accelerated,
        "targets_loaded": len(engine.list_targets())
    })

@app.route('/api/export_report')
def export_report():
    """Export all matches found this session as a CSV evidentiary report."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Video File", "Target", "Timestamp", "Frame Index", "Similarity %", "Detection Confidence %"])
    for m in session_matches:
        writer.writerow([
            os.path.basename(m.get("video_path") or ""),
            m.get("target_name", ""),
            m.get("timestamp_str", ""),
            m.get("frame_index", ""),
            f"{m.get('similarity', 0) * 100:.1f}",
            f"{m.get('score', 0) * 100:.1f}",
        ])

    filename = f"face_seeker_report_{time.strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.route('/video_feed')
def video_feed():
    def generate():
        while True:
            try:
                frame_bytes = frame_queue.get(timeout=1.0)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            except queue.Empty:
                pass
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/video_file')
def video_file():
    """
    Serve the currently loaded source video (with HTTP Range support) for the
    Review Timeline's native <video> player, enabling true seek-to-timestamp.
    Only ever serves the single path most recently loaded via the engine, to
    avoid exposing an arbitrary filesystem path traversal surface.
    """
    path = current_video_path.get("path")
    if not path or not os.path.exists(path):
        return jsonify({"success": False, "message": "No video loaded"}), 404
    return send_file(path, conditional=True)

@app.route('/api/stream')
def stream():
    def event_stream():
        while True:
            try:
                event_type, data = sse_queue.get(timeout=1.0)
                yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
            except queue.Empty:
                yield ": keep-alive\n\n"

    return Response(stream_with_context(event_stream()), mimetype="text/event-stream")

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    # When running directly, optionally open browser
    import threading, webbrowser
    threading.Timer(1.25, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    app.run(port=5000, threaded=True)
