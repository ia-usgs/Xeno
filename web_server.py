#!/usr/bin/env python3
"""
web_server.py

Flask HTTP server for Xeno Wi-Fi scan reports.
Index page just lists available SSIDs (no scan or vuln details).
"""

import os
from flask import Flask, send_from_directory, render_template

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


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.route('/')
def index():
    """
    Index page: only a list of all {SSID}.html files.
    """
    try:
        files = sorted(
            f for f in os.listdir(HTML_LOG_DIR)
            if f.endswith('.html')
        )
    except FileNotFoundError:
        files = []

    return render_template('index.html', files=files)


@app.route('/report/<path:filename>')
def report(filename):
    """
    Serve the raw report file from utils/html_logs.
    """
    return send_from_directory(HTML_LOG_DIR, filename)


@app.route('/static/<path:filename>')
def static_files(filename):
    """
    Serve CSS/JS/images from the static folder.
    """
    return send_from_directory(app.static_folder, filename)


# -----------------------------------------------------------------------------
# Entrypoint
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    # For production, swap this out for gunicorn or another WSGI server
    app.run(
        host='0.0.0.0',
        port=8080,
        debug=DEBUG,
        use_reloader=True
    )
