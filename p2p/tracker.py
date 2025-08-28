# p2p/tracker.py
import json, time, argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

TTL_SECONDS = 30 * 60  # peer record lifetime
# store: infoHash -> { "ip:port": last_seen_ts }
STORE = {}

def _now():
    return time.time()

def _prune():
    """Remove expired peers from STORE."""
    now = _now()
    for key in list(STORE.keys()):
        peers = STORE[key]
        for ep, ts in list(peers.items()):
            if now - ts > TTL_SECONDS:
                del peers[ep]
        if not peers:
            del STORE[key]

class Handler(BaseHTTPRequestHandler):
    def _send_json(self, obj, code=200):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/announce":
            self._send_json({"error": "not found"}, 404); return
        try:
            length = int(self.headers.get("Content-Length","0"))
            body = self.rfile.read(length)
            req = json.loads(body.decode())
            info_hash = req.get("infoHash")
            ip = req.get("ip")
            port = int(req.get("port"))
            if not info_hash or not ip or not port:
                self._send_json({"error": "missing fields"}, 400); return
            _prune()
            peers = STORE.setdefault(info_hash, {})
            peers[f"{ip}:{port}"] = _now()
            self._send_json({"ok": True, "count": len(peers)})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/peers":
            self._send_json({"error": "not found"}, 404); return
        qs = parse_qs(parsed.query)
        info_hash = (qs.get("infoHash") or [None])[0]
        if not info_hash:
            self._send_json({"error": "infoHash required"}, 400); return
        _prune()
        entries = []
        for ep, _ts in STORE.get(info_hash, {}).items():
            ip, port = ep.split(":")
            entries.append({"ip": ip, "port": int(port)})
        self._send_json({"peers": entries})

def main():
    ap = argparse.ArgumentParser("tracker")
    ap.add_argument("--port", type=int, default=7000)
    args = ap.parse_args()
    addr = ("0.0.0.0", args.port)
    print(f"[tracker] listening on http://{addr[0]}:{addr[1]}")
    httpd = ThreadingHTTPServer(addr, Handler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[tracker] stopped.")

if __name__ == "__main__":
    main()
