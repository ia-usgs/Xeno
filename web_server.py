#!/usr/bin/env python3
"""
web_server.py

Flask HTTP server for Xeno Wi-Fi scan reports and error logs.
"""

import os
import json
import shutil
import signal
import subprocess
import threading
from pathlib import Path
from flask import Flask, send_from_directory, render_template, jsonify, request, abort
from werkzeug.utils import secure_filename
from utils.logger import Logger

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
DEBUG = False

app = Flask(
    __name__,
    static_folder='static',
    template_folder='templates'
)

# Directory where per-SSID HTML logs live
HTML_LOG_DIR = os.path.join(os.path.dirname(__file__), 'utils', 'html_logs')
ERROR_LOG_FILE = os.path.join(os.path.dirname(__file__), 'logs', 'errors.json')


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.route('/')
def index():
    """Index page: list of all {SSID}.html files."""
    try:
        files = sorted(
            f for f in os.listdir(HTML_LOG_DIR)
            if f.endswith('.html')
        )
    except FileNotFoundError:
        files = []

    # Count errors for the nav badge
    error_count = _get_error_count()

    return render_template('index.html', files=files, error_count=error_count)


@app.route('/errors')
def errors_page():
    """Errors page: display all runtime errors."""
    errors = Logger.get_errors(limit=200)
    error_count = len(errors)
    return render_template('errors.html', errors=errors, error_count=error_count)


@app.route('/api/errors')
def api_errors():
    """JSON API endpoint for errors (for React frontend or polling)."""
    limit = int(os.environ.get('ERROR_LIMIT', 200))
    errors = Logger.get_errors(limit=limit)
    return jsonify({"errors": errors, "count": len(errors)})


@app.route('/api/errors/clear', methods=['POST'])
def api_clear_errors():
    """Clear all errors."""
    Logger.clear_errors()
    return jsonify({"status": "ok", "message": "Errors cleared."})


@app.route('/live')
def live_page():
    """Live activity feed page."""
    error_count = _get_error_count()
    events = Logger.get_activity(limit=100)
    return render_template('live.html', events=events, error_count=error_count)


@app.route('/api/activity')
def api_activity():
    """JSON API for live activity feed (supports polling)."""
    limit = int(os.environ.get('ACTIVITY_LIMIT', 100))
    ssid = None  # could parse from query string
    events = Logger.get_activity(limit=limit, ssid_filter=ssid)
    return jsonify({"events": events, "count": len(events)})


@app.route('/api/activity/clear', methods=['POST'])
def api_clear_activity():
    """Clear all activity events."""
    Logger.clear_activity()
    return jsonify({"status": "ok", "message": "Activity cleared."})


@app.route('/report/<path:filename>')
def report(filename):
    """Serve the raw report file from utils/html_logs."""
    return send_from_directory(HTML_LOG_DIR, filename)


@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve CSS/JS/images from the static folder."""
    return send_from_directory(app.static_folder, filename)


# -----------------------------------------------------------------------------
# File Manager
# -----------------------------------------------------------------------------
FILE_ROOT = os.path.expanduser("~")  # Default browsable root; change as needed

def _safe_path(requested: str) -> str:
    """Resolve and validate a path stays within FILE_ROOT."""
    base = os.path.realpath(FILE_ROOT)
    resolved = os.path.realpath(os.path.join(base, requested.lstrip("/")))
    if not resolved.startswith(base):
        abort(403, "Access denied")
    return resolved


def _format_size(size: int) -> str:
    for u in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {u}" if size != int(size) else f"{int(size)} {u}"
        size /= 1024
    return f"{size:.1f} TB"


@app.route('/files')
def files_page():
    """File manager page."""
    req_path = request.args.get("path", "/")
    abs_path = _safe_path(req_path)
    error_count = _get_error_count()

    entries = []
    try:
        for name in sorted(os.listdir(abs_path)):
            full = os.path.join(abs_path, name)
            try:
                stat = os.stat(full)
                rel = "/" + os.path.relpath(full, os.path.realpath(FILE_ROOT))
                entries.append({
                    "name": name,
                    "type": "directory" if os.path.isdir(full) else "file",
                    "size": stat.st_size if os.path.isfile(full) else 0,
                    "size_fmt": _format_size(stat.st_size) if os.path.isfile(full) else "—",
                    "modified": __import__("datetime").datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                    "path": rel,
                })
            except OSError:
                pass
    except PermissionError:
        pass

    # Sort: directories first, then files
    entries.sort(key=lambda e: (0 if e["type"] == "directory" else 1, e["name"].lower()))

    # Build breadcrumbs
    rel_path = "/" + os.path.relpath(abs_path, os.path.realpath(FILE_ROOT))
    if rel_path == "/.":
        rel_path = "/"
    parts = [p for p in rel_path.split("/") if p]
    breadcrumbs = []
    for i, part in enumerate(parts):
        breadcrumbs.append({"name": part, "path": "/" + "/".join(parts[:i+1])})

    parent_path = "/" + "/".join(parts[:-1]) if parts else "/"

    return render_template("files.html",
                           entries=entries,
                           current_path=rel_path,
                           breadcrumbs=breadcrumbs,
                           parent_path=parent_path,
                           error_count=error_count)


@app.route('/api/files')
def api_files():
    """JSON API: list directory contents."""
    req_path = request.args.get("path", "/")
    abs_path = _safe_path(req_path)

    entries = []
    try:
        for name in sorted(os.listdir(abs_path)):
            full = os.path.join(abs_path, name)
            try:
                stat = os.stat(full)
                rel = "/" + os.path.relpath(full, os.path.realpath(FILE_ROOT))
                entries.append({
                    "name": name,
                    "type": "directory" if os.path.isdir(full) else "file",
                    "size": stat.st_size if os.path.isfile(full) else 0,
                    "modified": __import__("datetime").datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                    "path": rel,
                })
            except OSError:
                pass
    except PermissionError:
        pass

    entries.sort(key=lambda e: (0 if e["type"] == "directory" else 1, e["name"].lower()))
    rel = "/" + os.path.relpath(abs_path, os.path.realpath(FILE_ROOT))
    if rel == "/.":
        rel = "/"
    return jsonify({"entries": entries, "current_path": rel})


@app.route('/api/files/download')
def api_download():
    """Download a file."""
    req_path = request.args.get("path", "")
    abs_path = _safe_path(req_path)
    if not os.path.isfile(abs_path):
        abort(404, "File not found")
    directory = os.path.dirname(abs_path)
    filename = os.path.basename(abs_path)
    return send_from_directory(directory, filename, as_attachment=True)


@app.route('/api/files/upload', methods=['POST'])
def api_upload():
    """Upload files to a directory."""
    target_path = request.form.get("path", "/")
    abs_dir = _safe_path(target_path)
    if not os.path.isdir(abs_dir):
        abort(400, "Target is not a directory")

    uploaded = []
    for f in request.files.getlist("files"):
        name = secure_filename(f.filename) if f.filename else "unnamed"
        dest = os.path.join(abs_dir, name)
        f.save(dest)
        uploaded.append(name)
    return jsonify({"status": "ok", "uploaded": uploaded})


@app.route('/api/files/delete', methods=['POST'])
def api_delete():
    """Delete a file or directory."""
    data = request.get_json(force=True)
    abs_path = _safe_path(data.get("path", ""))
    if os.path.isdir(abs_path):
        shutil.rmtree(abs_path)
    elif os.path.isfile(abs_path):
        os.remove(abs_path)
    else:
        abort(404, "Not found")
    return jsonify({"status": "ok"})


@app.route('/api/files/rename', methods=['POST'])
def api_rename():
    """Rename a file or directory."""
    data = request.get_json(force=True)
    abs_path = _safe_path(data.get("path", ""))
    new_name = secure_filename(data.get("new_name", ""))
    if not new_name:
        abort(400, "Invalid name")
    parent = os.path.dirname(abs_path)
    new_path = os.path.join(parent, new_name)
    if os.path.exists(new_path):
        abort(409, "Name already exists")
    os.rename(abs_path, new_path)
    return jsonify({"status": "ok"})


@app.route('/api/files/mkdir', methods=['POST'])
def api_mkdir():
    """Create a new directory."""
    data = request.get_json(force=True)
    parent = _safe_path(data.get("path", "/"))
    name = secure_filename(data.get("name", ""))
    if not name:
        abort(400, "Invalid name")
    new_dir = os.path.join(parent, name)
    os.makedirs(new_dir, exist_ok=True)
    return jsonify({"status": "ok"})


@app.route('/api/files/read')
def api_read_file():
    """Read a text file's contents."""
    req_path = request.args.get("path", "")
    abs_path = _safe_path(req_path)
    if not os.path.isfile(abs_path):
        abort(404, "File not found")
    # Limit to 2MB for safety
    if os.path.getsize(abs_path) > 2 * 1024 * 1024:
        abort(413, "File too large to edit (max 2MB)")
    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return jsonify({"status": "ok", "content": content, "path": req_path})
    except Exception as e:
        abort(500, f"Could not read file: {e}")


@app.route('/api/files/write', methods=['POST'])
def api_write_file():
    """Write content to a text file."""
    data = request.get_json(force=True)
    req_path = data.get("path", "")
    content = data.get("content", "")
    abs_path = _safe_path(req_path)
    if os.path.isdir(abs_path):
        abort(400, "Path is a directory")
    try:
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        return jsonify({"status": "ok"})
    except Exception as e:
        abort(500, f"Could not write file: {e}")


# -----------------------------------------------------------------------------
# Stop / Shutdown
# -----------------------------------------------------------------------------
@app.route('/api/stop', methods=['POST'])
def api_stop():
    """
    Kill the xeno scanner (main.py) then shut down this web server.
    Returns a JSON response before exiting so the browser gets confirmation.
    """
    # 1) Kill the scanner process by name
    try:
        result = subprocess.run(
            ["pkill", "-f", "main.py"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        scanner_killed = result.returncode == 0
    except Exception as e:
        scanner_killed = False

    Logger().log(f"[INFO] Stop requested via dashboard. Scanner killed: {scanner_killed}")

    # 2) Schedule server shutdown after 500ms so the response can be sent first
    def _shutdown():
        import time
        time.sleep(0.5)
        os._exit(0)

    threading.Thread(target=_shutdown, daemon=True).start()

    return jsonify({
        "status": "stopping",
        "scanner_killed": scanner_killed,
        "message": "Xeno is shutting down."
    })



def _get_error_count():
    """Get the number of errors for display in nav badges."""
    try:
        if os.path.exists(ERROR_LOG_FILE):
            with open(ERROR_LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
            return len(data.get("errors", []))
    except Exception:
        pass
    return 0


# -----------------------------------------------------------------------------
# Entrypoint
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=8080,
        debug=DEBUG,
        use_reloader=True
    )
