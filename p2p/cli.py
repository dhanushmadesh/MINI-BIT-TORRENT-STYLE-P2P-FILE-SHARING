# p2p/cli.py
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import random
import string
from pathlib import Path
from urllib import parse, request
from typing import Dict, Optional

from .meta import build_metadata, write_meta, read_meta
from .pieces import PieceStore
from .peer_server import PeerServer
from .peer_client import PeerClient

log = logging.getLogger(__name__)


def peer_id(n: int = 20) -> str:
    """Generate a random peer_id string (letters+digits)."""
    return "".join(random.choice(string.ascii_letters + string.digits) for _ in range(n))


# ---------------- tracker helpers ----------------
def _post_json(url: str, payload: Dict) -> Dict:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get_json(url: str) -> Dict:
    with request.urlopen(url, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))


async def tracker_announce(tracker: str, info_hash: str, ip: str, port: int) -> Dict:
    url = f"http://{tracker}/announce"
    payload = {"infoHash": info_hash, "ip": ip, "port": port}
    return await asyncio.to_thread(_post_json, url, payload)


async def tracker_peers(tracker: str, info_hash: str) -> Dict:
    url = f"http://{tracker}/peers?infoHash={parse.quote(info_hash)}"
    return await asyncio.to_thread(_get_json, url)


# ---------------- commands ----------------
def cmd_create(args: argparse.Namespace) -> None:
    meta = build_metadata(args.file, args.piece)
    out = Path(args.file).with_suffix(Path(args.file).suffix + ".p2pmeta")
    write_meta(meta, str(out))
    log.info("[create] wrote %s", out)
    log.info("[create] infoHash=%s pieces=%s", meta["infoHash"], len(meta["pieces"]))


async def cmd_seed_async(args: argparse.Namespace) -> None:
    meta = read_meta(args.meta)
    workdir = Path(args.workdir)
    store = PieceStore(meta, workdir)

    if args.source:
        n = store.ingest_from_source(args.source)
        log.info("[seed] ingested %s/%s verified pieces from %s", n, store.total, args.source)

    if args.tracker:
        try:
            res = await tracker_announce(args.tracker, meta["infoHash"], "127.0.0.1", args.port)
            log.info("[seed] announced to tracker %s → %s", args.tracker, res)
        except Exception as e:
            log.warning("[seed] tracker announce failed: %s", e)

    srv = PeerServer("0.0.0.0", args.port, meta, store, peer_id())
    log.info("[seed] serving %s (pieces=%s) on 0.0.0.0:%s", meta["name"], len(meta["pieces"]), args.port)
    await srv.serve()


def cmd_seed(args: argparse.Namespace) -> None:
    asyncio.run(cmd_seed_async(args))


async def cmd_download_async(args: argparse.Namespace) -> None:
    meta = read_meta(args.meta)
    store = PieceStore(meta, Path(args.workdir))

    host, port = None, None
    if args.from_peer:
        host, port = args.from_peer.split(":")
    elif args.tracker:
        try:
            data = await tracker_peers(args.tracker, meta["infoHash"])
            peers = data.get("peers", [])
            if not peers:
                raise RuntimeError("no peers from tracker")
            host, port = peers[0]["ip"], peers[0]["port"]
            log.info("[download] got peer from tracker: %s:%s", host, port)
        except Exception as e:
            raise RuntimeError(f"tracker lookup failed: {e}") from e
    else:
        raise RuntimeError("provide --from-peer or --tracker")

    cli = PeerClient(meta, store, peer_id())
    if args.parallel > 1:
        await cli.download_from_parallel(host, int(port), workers=args.parallel)
    else:
        await cli.download_from(host, int(port))


def cmd_download(args: argparse.Namespace) -> None:
    try:
        asyncio.run(cmd_download_async(args))
    except Exception as e:
        log.error("[download] error: %s", e)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    ap = argparse.ArgumentParser(prog="p2p", description="Mini P2P tool")
    sub = ap.add_subparsers(dest="cmd", required=True)

    # create
    pcreate = sub.add_parser("create", help="Create .p2pmeta for a file")
    pcreate.add_argument("file")
    pcreate.add_argument("--piece", type=int, default=1_048_576, help="piece size in bytes (default 1 MiB)")
    pcreate.set_defaults(func=cmd_create)

    # seed
    pseed = sub.add_parser("seed", help="Seed a file using its .p2pmeta")
    pseed.add_argument("meta", help="path to .p2pmeta")
    pseed.add_argument("--port", type=int, default=5001)
    pseed.add_argument("--workdir", default="./data", help="where .partial lives")
    pseed.add_argument("--source", default=None, help="(optional) path to the full source file to ingest")
    pseed.add_argument("--tracker", default=None, help="host:port of tracker (e.g., 127.0.0.1:7000)")
    pseed.set_defaults(func=cmd_seed)

    # download
    pget = sub.add_parser("download", help="Download using a peer or a tracker")
    pget.add_argument("meta", help="path to .p2pmeta")
    pget.add_argument("--from-peer", required=False, help="HOST:PORT of a peer")
    pget.add_argument("--tracker", default=None, help="host:port of tracker (e.g., 127.0.0.1:7000)")
    pget.add_argument("--workdir", default="./downloads", help="where to store the file")
    pget.add_argument("--parallel", type=int, default=1, help="number of parallel connections")
    pget.set_defaults(func=cmd_download)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
