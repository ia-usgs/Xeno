from flask import Flask, send_from_directory, render_template_string
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

@app.route('/display/live')
def display_live_image():
    """Serve the current display image directly."""
    try:
        return send_from_directory('.', 'latest_display.png')
    except FileNotFoundError:
        # Return a placeholder if no display image exists yet
        from flask import Response
        return Response("Display image not available yet. The display will appear here once Xeno starts scanning.", 
                       status=404, mimetype='text/plain')

@app.route('/display/feed')
def display_feed():
    """Serve an auto-refreshing HTML page showing the current display."""
    feed_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Xeno Live Display Feed</title>
        <link href="https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="/static/logTheme.css">
        <style>
            .display-container {
                text-align: center;
                padding: 2rem;
            }
            .display-image {
                border: 2px solid #22d3ee;
                border-radius: 8px;
                background-color: #1e293b;
                padding: 1rem;
                display: inline-block;
                box-shadow: 0 0 10px rgba(34, 211, 238, 0.3);
            }
            .display-image img {
                max-width: 100%;
                height: auto;
                image-rendering: pixelated; /* Preserve crisp edges for e-ink display */
            }
            .refresh-info {
                margin-top: 1rem;
                color: #94a3b8;
                font-size: 0.9rem;
            }
        </style>
        <script>
            // Auto-refresh the image every 2 seconds
            function refreshDisplay() {
                const img = document.getElementById('display-img');
                const timestamp = new Date().getTime();
                img.src = '/display/live?' + timestamp;
            }
            
            // Set up auto-refresh
            setInterval(refreshDisplay, 2000);
            
            // Also refresh when the page becomes visible again
            document.addEventListener('visibilitychange', function() {
                if (!document.hidden) {
                    refreshDisplay();
                }
            });
        </script>
    </head>
    <body>
        <header>
            <h1>Xeno Live Display Feed</h1>
        </header>
        
        <div class="display-container">
            <div class="display-image">
                <img id="display-img" src="/display/live" alt="Xeno E-Ink Display" onerror="this.alt='Display image not available'">
            </div>
            <div class="refresh-info">
                Live feed • Updates every 2 seconds
            </div>
        </div>
        
        <footer>
            <a href="javascript:history.back()" style="color: #22d3ee;">← Back to Reports</a>
        </footer>
    </body>
    </html>
    """
    return render_template_string(feed_html)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
