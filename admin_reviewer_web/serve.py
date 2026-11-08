#!/usr/bin/env python3
"""Static server; /login and /login/ redirect to /login.html (fixes asset paths)."""
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
ALIASES = {
    "/login": "/login.html",
    "/app": "/app.html",
    "/forgot-password": "/forgot-password.html",
}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _redirect_alias(self) -> bool:
        parsed = urlparse(self.path)
        key = parsed.path.rstrip("/") or "/"
        target = ALIASES.get(key)
        if not target or parsed.path == target:
            return False
        dest = target + (f"?{parsed.query}" if parsed.query else "")
        self.send_response(302)
        self.send_header("Location", dest)
        self.end_headers()
        return True

    def do_GET(self):
        if self._redirect_alias():
            return
        return super().do_GET()

    def do_HEAD(self):
        if self._redirect_alias():
            return
        return super().do_HEAD()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5173
    print(f"FacultyLink web: http://localhost:{port}/")
    print(f"  Login: http://localhost:{port}/login.html")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
