"""Run: python app.py. Standard-library HTTP server + SQLite, no pip required."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlparse
import argparse
import json
import os
import secrets
import sqlite3
import webbrowser
import engine

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("TYAGA_DATABASE", str(ROOT / "tyaga.sqlite3")))


def database():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.execute("CREATE TABLE IF NOT EXISTS demos (session TEXT PRIMARY KEY, data TEXT NOT NULL)")
    return conn


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "dist"), **kwargs)

    def log_message(self, fmt, *args):
        if self.path.startswith("/api/"):
            return
        super().log_message(fmt, *args)

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        super().end_headers()

    def api(self, action, payload):
        cookie = SimpleCookie()
        try: cookie.load(self.headers.get("Cookie", ""))
        except Exception: pass
        session = cookie["tyaga_demo"].value if "tyaga_demo" in cookie else secrets.token_urlsafe(32)
        if not 20 <= len(session) <= 100: session = secrets.token_urlsafe(32)
        conn = database()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT data FROM demos WHERE session=?", (session,)).fetchone()
            result = engine.request(row[0] if row else "", action, json.dumps(payload, ensure_ascii=False))
            response = json.loads(result)
            if response["ok"]:
                conn.execute("INSERT INTO demos(session,data) VALUES(?,?) ON CONFLICT(session) DO UPDATE SET data=excluded.data", (session, json.dumps(response["state"], ensure_ascii=False)))
            conn.commit()
        finally:
            conn.close()
        data = result.encode("utf-8")
        self.send_response(200 if response["ok"] else 400)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Set-Cookie", "tyaga_demo=" + session + "; Path=/; HttpOnly; SameSite=Strict")
        self.end_headers(); self.wfile.write(data)

    def do_GET(self):
        if self.path.split("?")[0] == "/api/bootstrap":
            return self.api("bootstrap", {})
        if self.path.split("?")[0] == "/server-mode.js":
            data = b"window.TYAGA_SERVER = true;"
            self.send_response(200); self.send_header("Content-Type", "text/javascript"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
            return
        return super().do_GET()

    def do_POST(self):
        if self.path != "/api/action":
            self.send_error(404); return
        origin = self.headers.get("Origin")
        if origin and urlparse(origin).netloc != self.headers.get("Host"):
            self.send_error(403, "Origin mismatch"); return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 25_000_000: raise ValueError()
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict) or not isinstance(data.get("action"), str): raise ValueError()
        except (ValueError, TypeError):
            self.send_error(400, "Invalid JSON body"); return
        return self.api(data["action"], data.get("payload", {}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ТЯГА — локальное демо на Python")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"ТЯГА: http://{args.host}:{args.port}\nДемо-код входа: 123456. Остановка: Ctrl+C", flush=True)
    if args.open: webbrowser.open(f"http://{args.host}:{args.port}")
    try: server.serve_forever()
    except KeyboardInterrupt: server.server_close()
