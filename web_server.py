from flask import Flask, send_from_directory
import os

app = Flask(__name__, static_folder='static')
HTML_LOG_DIR = os.path.join(os.path.dirname(__file__), 'utils/html_logs')

@app.route('/')
def index():
    files = [f for f in os.listdir(HTML_LOG_DIR) if f.endswith('.html')]
    file_links = ''.join(f'<li><a href="/report/{f}">{f}</a></li>' for f in files)
    return f"<h1>Xeno Reports</h1><ul>{file_links}</ul>"

@app.route('/report/<path:filename>')
def report(filename):
    return send_from_directory(HTML_LOG_DIR, filename)

# This is automatic with Flask, but explicitly routing it helps on older setups
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(app.static_folder, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
