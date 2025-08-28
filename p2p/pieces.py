# p2p/pieces.py
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Optional, Set

from .meta import sha256_hex

log = logging.getLogger(__name__)


class PieceStore:
    """
    Stores verified pieces on disk and tracks which pieces we have.
    Persists state in '<filename>.state.json' so downloads can resume.
    """

    def __init__(self, meta: Dict, workdir: Path):
        self.meta = meta
        self.dir = Path(workdir)
        self.dir.mkdir(parents=True, exist_ok=True)

        self.piece_len: int = meta["pieceLength"]
        self.total: int = len(meta["pieces"])
        self._partial: Path = self.dir / (self.meta["name"] + ".partial")
        self._state_path: Path = self.dir / (self.meta["name"] + ".state.json")

        self.have: Set[int] = set()
        self._load_state()

    # ---------------- state persistence ----------------
    def _load_state(self) -> None:
        """Load which pieces we already have from state file (if present)."""
        if self._state_path.exists():
            try:
                data = json.loads(self._state_path.read_text(encoding="utf-8"))
                indices = data.get("have", [])
                # validate bounds
                self.have = {i for i in indices if 0 <= i < self.total}
                log.debug("[pieces] loaded state: %s pieces", len(self.have))
            except Exception as e:
                log.warning("[pieces] failed to load state: %s", e)
                self.have = set()

    def _save_state(self) -> None:
        """Save current piece set to disk (non-fatal if it fails)."""
        try:
            payload = {"have": sorted(self.have), "total": self.total}
            self._state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as e:
            log.warning("[pieces] failed to save state: %s", e)

    # ---------------- piece I/O ----------------
    def write_piece(self, index: int, data: bytes) -> bool:
        """
        Verify hash and write a piece to the correct offset; persist state.

        Returns True if accepted, False otherwise.
        """
        if index < 0 or index >= self.total:
            return False
        if sha256_hex(data) != self.meta["pieces"][index]:
            log.warning("[pieces] hash mismatch on piece %s", index)
            return False

        mode = "r+b" if self._partial.exists() else "wb"
        with open(self._partial, mode) as f:
            f.seek(index * self.piece_len)
            f.write(data)

        self.have.add(index)
        self._save_state()
        return True

    def read_piece(self, index: int) -> Optional[bytes]:
        """
        Read a piece from disk; trims the last piece to the real file size.
        Returns None if not present.
        """
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

    # ---------------- status helpers ----------------
    def is_complete(self) -> bool:
        """Return True if all pieces are present."""
        return len(self.have) == self.total

    def finalize(self) -> Optional[Path]:
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
        if not src.exists():
            raise FileNotFoundError(f"Source file not found: {src}")

        count = 0
        with open(src, "rb") as f:
            for idx in range(self.total):
                data = f.read(self.piece_len)
                if not data:
                    break
                if self.write_piece(idx, data):
                    count += 1
        log.info("[pieces] ingested %s/%s pieces from %s", count, self.total, src)
        return count
