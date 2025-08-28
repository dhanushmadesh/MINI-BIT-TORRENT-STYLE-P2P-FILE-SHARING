# p2p/tracker.py
from __future__ import annotations

import argparse
import json
import logging
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from typing import Dict, Tuple

TTL_SECONDS = 30 * 60  # peer record lifetime
# STORE maps infoHash -> { "ip:port": last_seen_ts }
STORE: Dict[str, Dict[str, float]] = {}

log = logging.getLogger(__name__)


def _now() -> float:
    return time.time()


def _prune() -> None:
    """Remove expired peers from STORE."""
    now = _now()
    removed = 0
    for key in list(STORE.keys()):
        peers = STORE[key]
        for ep, ts in list(peers.items()):
            if now - ts > TTL_SECONDS:
                del peers[ep]
                removed += 1
        if not peers:
            del STORE[key]
    if removed:
        log.debug("[tracker] pruned %s expired peers", removed)


class Handler(BaseHTTPRequestHandler):
    """HTTP handler implementing /announce (POST) and /peers (GET)."""

    def _send_json(self, obj: Dict, code: int = 200) -> None:
        data = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args) -> None:
        # suppress default noisy HTTP logs; rely on our logging instead
        log.info("[tracker] %s - %s", self.address_string(), format % args)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/announce":
            self._send_json({"error": "not found"}, 404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length)
            req = json.loads(body.decode("utf-8"))

            info_hash = req.get("infoHash")
            ip = req.get("ip")
            port = int(req.get("port", 0))

            if not info_hash or not ip or not port:
                self._send_json({"error": "missing fields"}, 400)
                return

            _prune()
            peers = STORE.setdefault(info_hash, {})
            peers[f"{ip}:{port}"] = _now()
            self._send_json({"ok": True, "count": len(peers)})
            log.info("[tracker] announce %s:%s for %s (total=%s)", ip, port, info_hash, len(peers))

        except Exception as e:
            log.error("[tracker] announce error: %s", e)
            self._send_json({"error": str(e)}, 500)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/peers":
            self._send_json({"error": "not found"}, 404)
            return

        qs = parse_qs(parsed.query)
        info_hash = (qs.get("infoHash") or [None])[0]
        if not info_hash:
            self._send_json({"error": "infoHash required"}, 400)
            return

        _prune()
        entries = []
        for ep, _ts in STORE.get(info_hash, {}).items():
            ip, port = ep.split(":")
            entries.append({"ip": ip, "port": int(port)})
        self._send_json({"peers": entries})
        log.info("[tracker] served %s peers for %s", len(entries), info_hash)


def main() -> None:
    ap = argparse.ArgumentParser("tracker")
    ap.add_argument("--port", type=int, default=7000)
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    addr: Tuple[str, int] = ("0.0.0.0", args.port)
    log.info("[tracker] listening on http://%s:%s", addr[0], addr[1])

    httpd = ThreadingHTTPServer(addr, Handler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        log.info("\n[tracker] stopped.")


if __name__ == "__main__":
    main()
