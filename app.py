import os
import sys
import cv2
import json
import queue
import threading
import webview
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from werkzeug.utils import secure_filename
from face_engine import FaceEngine, EngineState

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Global engine instance
engine = FaceEngine()

# Queues for web streaming
frame_queue = queue.Queue(maxsize=2)
sse_queue = queue.Queue(maxsize=100)

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
    match_filename = f"match_{match.frame_index}.jpg"
    match_path = os.path.join(app.config['UPLOAD_FOLDER'], match_filename)
    cv2.imwrite(match_path, match.face_crop)
    
    match_dict = {
        "frame_index": match.frame_index,
        "timestamp_str": match.timestamp_str,
        "similarity": match.similarity,
        "score": match.score,
        "image_url": f"/uploads/{match_filename}"
    }
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
        allow_multiple=False,
        file_types=('Image Files (*.jpg;*.jpeg;*.png;*.bmp)', 'All Files (*.*)')
    )
    
    if not result or len(result) == 0:
        return jsonify({"success": False, "message": "No file selected"})
        
    file_path = result[0]
    res = engine.load_target_image(file_path)
    if res.success:
        return jsonify({"success": True, "message": "Target loaded", "path": file_path})
    else:
        return jsonify({"success": False, "message": res.message})

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

@app.route('/api/action', methods=['POST'])
def action():
    data = request.json
    cmd = data.get('command')
    
    if cmd == 'start':
        video_path = data.get('video_path')
        if not video_path:
            return jsonify({"success": False, "message": "No video selected"})
        try:
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
    data = request.json
    cosine = data.get('cosine')
    if cosine is not None:
        engine.set_thresholds(cosine_threshold=float(cosine))
    return jsonify({"success": True})

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
    from flask import send_from_directory
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    # When running directly, optionally open browser
    import threading, webbrowser
    threading.Timer(1.25, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    app.run(port=5000, threaded=True)
