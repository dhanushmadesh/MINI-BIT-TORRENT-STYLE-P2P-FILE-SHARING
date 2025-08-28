# p2p/meta.py
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Dict, List


def sha256_hex(b: bytes) -> str:
    """Return the hex SHA-256 of raw bytes."""
    return hashlib.sha256(b).hexdigest()


def _compute_infohash(core: Dict) -> str:
    """
    Compute a stable infoHash from the canonical JSON of the metadata core.
    Canonicalization uses sorted keys and no extra whitespace.
    """
    canonical = json.dumps(core, sort_keys=True, separators=(",", ":")).encode()
    return sha256_hex(canonical)


def build_metadata(file_path: str, piece_len: int = 1_048_576) -> Dict:
    """
    Build the metadata dict for a given file.

    Args:
        file_path: Path to the source file to describe.
        piece_len: Piece size in bytes (default 1 MiB). Must be > 0.

    Returns:
        A dict containing: name, size, pieceLength, pieces[], infoHash.

    Raises:
        FileNotFoundError: If file_path does not exist.
        ValueError: If piece_len <= 0 or file is empty.
    """
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    if piece_len <= 0:
        raise ValueError("piece_len must be > 0")

    size = p.stat().st_size
    if size == 0:
        raise ValueError(f"File is empty: {p}")

    pieces: List[str] = []
    with p.open("rb") as f:
        while True:
            chunk = f.read(piece_len)
            if not chunk:
                break
            pieces.append(sha256_hex(chunk))

    core = {
        "name": p.name,
        "size": size,
        "pieceLength": piece_len,
        "pieces": pieces,
    }
    core["infoHash"] = _compute_infohash(core)
    return core


def write_meta(meta: Dict, out_path: str) -> None:
    """
    Write metadata dict to JSON file.

    Args:
        meta: The metadata dict produced by build_metadata().
        out_path: Destination .p2pmeta path.
    """
    Path(out_path).write_text(json.dumps(meta, indent=2), encoding="utf-8")


def read_meta(meta_path: str) -> Dict:
    """
    Read a .p2pmeta JSON file and return the dict.

    Also re-computes infoHash from the core fields and ensures it matches.

    Raises:
        FileNotFoundError: If meta_path does not exist.
        ValueError: If required fields are missing or infoHash mismatch.
    """
    p = Path(meta_path)
    if not p.exists():
        raise FileNotFoundError(f"Meta file not found: {p}")

    data = json.loads(p.read_text(encoding="utf-8"))

    required = {"name", "size", "pieceLength", "pieces", "infoHash"}
    missing = required - set(data.keys())
    if missing:
        raise ValueError(f"Invalid meta: missing keys {sorted(missing)}")

    # Validate infoHash matches canonical core (defensive)
    core = {
        "name": data["name"],
        "size": data["size"],
        "pieceLength": data["pieceLength"],
        "pieces": data["pieces"],
    }
    expected = _compute_infohash(core)
    if data.get("infoHash") != expected:
        raise ValueError(
            "infoHash mismatch: file may be corrupted or edited.\n"
            f" expected={expected}\n actual={data.get('infoHash')}"
        )
    return data


# ---- Tiny CLI: create/show ----
def _cli_create(args: argparse.Namespace) -> None:
    meta = build_metadata(args.file, args.piece)
    out = Path(args.file).with_suffix(Path(args.file).suffix + ".p2pmeta")
    write_meta(meta, str(out))
    print(f"[meta] wrote {out}")
    print(f"[meta] infoHash={meta['infoHash']} pieces={len(meta['pieces'])}")


def _cli_show(args: argparse.Namespace) -> None:
    meta = read_meta(args.meta)
    print(json.dumps(meta, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser(prog="p2p.meta", description="Metadata tools")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pcreate = sub.add_parser("create", help="Create .p2pmeta for a file")
    pcreate.add_argument("file")
    pcreate.add_argument(
        "--piece", type=int, default=1_048_576, help="piece size in bytes (default 1 MiB)"
    )
    pcreate.set_defaults(func=_cli_create)

    pshow = sub.add_parser("show", help="Print a .p2pmeta file")
    pshow.add_argument("meta")
    pshow.set_defaults(func=_cli_show)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

