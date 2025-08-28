# run_download.py
from __future__ import annotations

import argparse
import asyncio
import logging
import random
import string
from pathlib import Path

from p2p.meta import read_meta
from p2p.pieces import PieceStore
from p2p.peer_client import PeerClient


def peer_id(n: int = 20) -> str:
    """Generate a random peer_id string."""
    return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(n))


async def main_async(args: argparse.Namespace) -> None:
    """Start downloading from a peer using a .p2pmeta file."""
    meta = read_meta(args.meta)
    store = PieceStore(meta, Path(args.workdir))
    cli = PeerClient(meta, store, peer_id())

    if args.parallel > 1:
        await cli.download_from_parallel(args.host, args.port, workers=args.parallel)
    else:
        await cli.download_from(args.host, args.port)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    ap = argparse.ArgumentParser("run_download", description="Download a file from a peer")
    ap.add_argument("--meta", required=True, help="Path to .p2pmeta file")
    ap.add_argument("--host", required=True, help="Peer host/IP")
    ap.add_argument("--port", type=int, required=True, help="Peer port")
    ap.add_argument("--workdir", default="./downloads", help="Folder where file is stored")
    ap.add_argument("--parallel", type=int, default=1, help="Number of parallel connections")
    args = ap.parse_args()

    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        logging.info("\n[download] stopped.")


if __name__ == "__main__":
    main()
