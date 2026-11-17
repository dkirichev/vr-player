#!/usr/bin/env python3
"""Local server for the VR viewer. Needed because browsers won't use file:// pages as WebGL video sources.
Usage: serve.py [VIDEO] [--port N] [--host H]
  VIDEO  optional file to preload; otherwise just drag & drop into the page."""
import argparse, json, os, re, sys
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

ap = argparse.ArgumentParser()
ap.add_argument('video', nargs='?', help='optional video to preload in the viewer')
ap.add_argument('--port', type=int, default=8000)
ap.add_argument('--host', default='127.0.0.1', help='default localhost only')
a = ap.parse_args()
HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(HERE, 'index.html')
VIDEO = os.path.abspath(a.video) if a.video else None
if VIDEO and not os.path.isfile(VIDEO):
    sys.exit(f'video not found: {VIDEO}')

class H(BaseHTTPRequestHandler):
    def log_message(self, *x): pass
    def _send_file(self, path, ctype):
        size = os.path.getsize(path)
        m = re.match(r'bytes=(\d*)-(\d*)', self.headers.get('Range', ''))
        start, end = 0, size - 1
        if m and (m[1] or m[2]):
            if m[1]: start = int(m[1]); end = int(m[2]) if m[2] else size - 1
            else: start = max(0, size - int(m[2]))  # suffix range
            end = min(end, size - 1)
            if start > end:
                self.send_response(416); self.send_header('Content-Range', f'bytes */{size}'); self.end_headers(); return
        code = 206 if m else 200
        self.send_response(code)
        self.send_header('Content-Type', ctype); self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Length', str(end - start + 1))
        if m: self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.end_headers()
        if self.command == 'HEAD': return
        with open(path, 'rb') as f:
            f.seek(start); n = end - start + 1
            try:
                while n > 0:
                    d = f.read(min(1 << 20, n))
                    if not d: break
                    self.wfile.write(d); n -= len(d)
            except (BrokenPipeError, ConnectionResetError):
                pass  # client closed connection (normal when seeking)
    def do_GET(self):
        p = self.path.split('?')[0]
        if p in ('/', '/index.html'): self._send_file(INDEX, 'text/html; charset=utf-8')
        elif p == '/__info':
            b = json.dumps({'video': os.path.basename(VIDEO) if VIDEO else None}).encode()
            self.send_response(200); self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)
        elif p == '/__video' and VIDEO: self._send_file(VIDEO, 'video/mp4')
        else:
            self.send_error(404)
    do_HEAD = do_GET

srv = ThreadingHTTPServer((a.host, a.port), H)
print(f'VR viewer: http://{a.host}:{a.port}   (preload: {VIDEO or "none, drag & drop a file"})   Ctrl+C to stop', flush=True)
try: srv.serve_forever()
except KeyboardInterrupt: print('\nstopped')
