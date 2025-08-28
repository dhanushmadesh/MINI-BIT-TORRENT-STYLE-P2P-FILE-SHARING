import json, hashlib
from pathlib import Path

def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def build_metadata(file_path: str, piece_len: int = 1_048_576) -> dict:
    p = Path(file_path); size = p.stat().st_size
    pieces = []
    with p.open('rb') as f:
        while True:
            chunk = f.read(piece_len)
            if not chunk: break
            pieces.append(sha256_hex(chunk))
    core = {"name": p.name, "size": size, "pieceLength": piece_len, "pieces": pieces}
    canonical = json.dumps(core, sort_keys=True, separators=(',', ':')).encode()
    core["infoHash"] = sha256_hex(canonical)
    return core

def write_meta(meta: dict, out_path: str):
    Path(out_path).write_text(json.dumps(meta, indent=2))

def read_meta(meta_path: str) -> dict:
    return json.loads(Path(meta_path).read_text())
