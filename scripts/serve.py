#!/usr/bin/env python3
"""Preview the built site the way GitHub Pages will serve it.

    python scripts/build.py && python scripts/serve.py        # then open http://localhost:8000/blogs/

The site is a project site, so it lives under a base path (site.json "base"). This server mounts
_site/ at that path, redirects / to it, and serves 404.html for anything missing, which is exactly
what GitHub Pages does. Pass a port as the only argument to use something other than 8000.
"""
import json, pathlib, sys, http.server, functools, posixpath, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = json.loads((ROOT / "site.json").read_text())
BASE = SITE["base"].rstrip("/")
OUT = ROOT / "_site"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000


class Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = urllib.parse.urlsplit(path).path
        if BASE and (path == BASE or path.startswith(BASE + "/")):
            path = path[len(BASE):] or "/"
        elif BASE:
            path = "/__outside__"
        return super().translate_path(path)

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        if BASE and not path.startswith(BASE):
            target = BASE + "/" if path in ("", "/") else BASE + path
            self.send_response(302); self.send_header("Location", target); self.end_headers(); return
        fs = pathlib.Path(self.translate_path(self.path))
        if fs.is_dir() and not path.endswith("/"):
            self.send_response(301); self.send_header("Location", path + "/"); self.end_headers(); return
        if not fs.exists() or (fs.is_dir() and not (fs / "index.html").exists()):
            self.send_response(404); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers()
            self.wfile.write((OUT / "404.html").read_bytes()); return
        super().do_GET()

    def log_message(self, fmt, *args):
        sys.stderr.write("  %s\n" % (fmt % args))


if __name__ == "__main__":
    if not OUT.exists():
        sys.exit("_site/ does not exist yet: run  python scripts/build.py  first")
    handler = functools.partial(Handler, directory=str(OUT))
    with http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler) as srv:
        print(f"serving _site/ at http://localhost:{PORT}{BASE}/   (Ctrl-C to stop)")
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print()
