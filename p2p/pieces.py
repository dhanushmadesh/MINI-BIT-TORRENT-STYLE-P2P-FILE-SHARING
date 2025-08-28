from pathlib import Path
import json
from .meta import sha256_hex

class PieceStore:
    """
    Stores verified pieces on disk and tracks which pieces we have.
    Persists state in '<filename>.state.json' so downloads can resume.
    """
    def __init__(self, meta: dict, workdir: Path):
        self.meta = meta
        self.dir = Path(workdir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.piece_len = meta["pieceLength"]
        self.total = len(meta["pieces"])
        self._partial = self.dir / (self.meta["name"] + ".partial")
        self._state_path = self.dir / (self.meta["name"] + ".state.json")
        self.have = set()
        self._load_state()

    def _load_state(self):
        if self._state_path.exists():
            try:
                data = json.loads(self._state_path.read_text())
                indices = data.get("have", [])
                # validate bounds
                self.have = {i for i in indices if 0 <= i < self.total}
            except Exception:
                self.have = set()

    def _save_state(self):
        try:
            payload = {"have": sorted(self.have), "total": self.total}
            self._state_path.write_text(json.dumps(payload, indent=2))
        except Exception:
            # non-fatal: state file failing shouldn't break download
            pass

    def write_piece(self, index: int, data: bytes) -> bool:
        """Verify hash and write a piece to the correct offset; persist state."""
        if index < 0 or index >= self.total:
            return False
        if sha256_hex(data) != self.meta["pieces"][index]:
            return False  # integrity check failed
        mode = "r+b" if self._partial.exists() else "wb"
        with open(self._partial, mode) as f:
            f.seek(index * self.piece_len)
            f.write(data)
        self.have.add(index)
        self._save_state()
        return True

    def read_piece(self, index: int) -> bytes | None:
        """Read a piece from disk; trims the last piece to the real file size."""
        if not self._partial.exists():
            return None
        if index < 0 or index >= self.total:
            return None
        with open(self._partial, "rb") as f:
            f.seek(index * self.piece_len)
            data = f.read(self.piece_len)
        # Trim last piece to true size
        if index == self.total - 1:
            last_size = self.meta["size"] - self.piece_len * (self.total - 1)
            data = data[:last_size]
        return data

    def is_complete(self) -> bool:
        return len(self.have) == self.total

    def finalize(self) -> Path | None:
        """
        Rename '<name>.partial' to the final file once all pieces are present.
        Removes the state file on success.
        """
        if self.is_complete() and self._partial.exists():
            final_path = self.dir / self.meta["name"]
            self._partial.replace(final_path)
            try:
                if self._state_path.exists():
                    self._state_path.unlink()
            except Exception:
                pass
            return final_path
        return None

    def ingest_from_source(self, source_path: str) -> int:
        """
        Reads the source file piece-by-piece, verifies each piece hash,
        and writes it into '<name>.partial' so this node can seed.
        Does not call finalize().
        Returns number of pieces successfully ingested.
        """
        src = Path(source_path)
        count = 0
        with open(src, "rb") as f:
            for idx in range(self.total):
                data = f.read(self.piece_len)
                if not data:
                    break
                if self.write_piece(idx, data):
                    count += 1
        return count
