# run_seed.py
from __future__ import annotations

import argparse
import asyncio
import logging
import random
import socket
import string
from pathlib import Path

from p2p.meta import read_meta
from p2p.pieces import PieceStore
from p2p.peer_server import PeerServer


def peer_id(n: int = 20) -> str:
    """Generate a random peer_id string."""
    return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(n))


def local_ip() -> str:
    """Try to detect the local LAN IP (fallback to 127.0.0.1)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        try:
            s.close()
        except Exception:
            pass
    return ip


async def main_async(args: argparse.Namespace) -> None:
    """Start seeding from a .p2pmeta file and optional source file."""
    meta = read_meta(args.meta)
    store = PieceStore(meta, Path(args.workdir))

    # ingest source file if we don’t already have all pieces
    if not store.is_complete() and args.source:
        src = Path(args.source)
        if not src.exists():
            raise FileNotFoundError(f"Source file not found: {src}")
        got = store.ingest_from_source(str(src))
        logging.info("[seed] ingested %s/%s verified pieces from %s", got, store.total, src)

    ip = local_ip()
    srv = PeerServer("0.0.0.0", args.port, meta, store, peer_id())

    logging.info("[seed] serving %s (pieces=%s) on %s:%s",
                 meta["name"], len(meta["pieces"]), ip, args.port)
    logging.info("[seed] hint: on downloader → "
                 "python run_download.py --meta %s --from-peer %s:%s",
                 args.meta, ip, args.port)

    await srv.serve()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    ap = argparse.ArgumentParser("run_seed", description="Start seeding a file")
    ap.add_argument("--meta", required=True, help="Path to .p2pmeta")
    ap.add_argument("--source", default=None,
                    help="Optional: full source file path to ingest (only needed once)")
    ap.add_argument("--workdir", default="./data", help="Working folder for partial/state files")
    ap.add_argument("--port", type=int, default=5001, help="Peer server port")

    args = ap.parse_args()

    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        logging.info("\n[seed] stopped.")


if __name__ == "__main__":
    main()
