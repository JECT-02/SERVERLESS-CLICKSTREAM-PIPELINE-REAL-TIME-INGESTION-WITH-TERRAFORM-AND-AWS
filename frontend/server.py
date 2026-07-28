import http.server
import json
import os
import re
import urllib.error
import urllib.request
FRONTEND_DIR = os.path.join(os.path.dirname(__file__) or '.', '.')
CONFIG_FILE = os.path.join(FRONTEND_DIR, 'config.js')
API_ID_FILE = os.path.join(FRONTEND_DIR, '.api_id')
_API_ID = None


def _get_api_id():
    global _API_ID
    if _API_ID:
        return _API_ID
    env_id = os.environ.get('API_ID')
    if env_id:
        _API_ID = env_id
        return _API_ID
    try:
        with open(API_ID_FILE) as f:
            content = f.read().strip()
            if content:
                _API_ID = content
                return _API_ID
    except FileNotFoundError:
        pass
    try:
        with open(CONFIG_FILE) as f:
            content = f.read()
        m = re.search(r'restapis/([^/]+)', content)
        if m:
            _API_ID = m.group(1)
            return _API_ID
    except FileNotFoundError:
        pass
    _API_ID = os.environ.get('API_ID', '91325a63cc')
    return _API_ID

API_URL = f"http://localhost:4566/restapis/{_get_api_id()}/prod/_user_request_/events"
print(f"Proxying API events to {API_URL}")


import traceback


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        try:
            super().__init__(*args, directory=FRONTEND_DIR, **kwargs)
        except Exception:
            traceback.print_exc()

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        if self.path != '/api/events':
            self.send_response(404)
            self.end_headers()
            return
        cl = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(cl)
        req = urllib.request.Request(
            API_URL, data=body,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = resp.read()
                self.send_response(resp.status)
                self._cors()
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_response(502)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def do_GET(self):
        if self.path == '/':
            self.path = '/index.html'
        super().do_GET()

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'OPTIONS,POST')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def log_message(self, format, *args):
        msg = ' '.join(str(a) for a in args) if args else format
        print(f"[{self.client_address[0]}] {msg}")


if __name__ == '__main__':
    port = 8000
    server = http.server.HTTPServer(('0.0.0.0', port), Handler)
    print(f'Serving frontend + proxy on http://localhost:{port}')
    server.serve_forever()
