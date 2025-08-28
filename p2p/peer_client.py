# p2p/peer_client.py
from __future__ import annotations

import asyncio
import base64
import logging
from typing import Dict, Optional, Tuple

from .wire import send_msg, recv_msg

log = logging.getLogger(__name__)


class PeerClient:
    """
    Minimal peer client:
    - Supports single-connection sequential download (baseline).
    - Supports multi-connection parallel download (workers split pieces).
    """

    def __init__(self, meta: Dict, store, peer_id: str):
        self.meta = meta
        self.store = store
        self.peer_id = peer_id
        self._write_lock = asyncio.Lock()  # protect concurrent writes to .partial

    # ---------------- connection helpers ----------------
    async def _handshake_and_bitfield(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> Dict:
        """
        Perform handshake and receive bitfield from peer.
        Raises RuntimeError if handshake fails.
        """
        await send_msg(
            writer,
            {"type": "handshake", "infoHash": self.meta["infoHash"], "peerId": self.peer_id},
        )

        hs = await recv_msg(reader)
        bf = await recv_msg(reader)

        if not hs or hs.get("type") != "handshake" or hs.get("infoHash") != self.meta["infoHash"]:
            writer.close()
            raise RuntimeError("Handshake failed")

        return bf or {}

    # ---------------- sequential download ----------------
    async def download_from(self, host: str, port: int) -> None:
        """
        Single connection, sequential requests (baseline).
        """
        reader, writer = await asyncio.open_connection(host, port)
        await self._handshake_and_bitfield(reader, writer)

        total = len(self.meta["pieces"])
        need = sorted(set(range(total)) - self.store.have)
        log.info("[client] requesting %s pieces sequentially", len(need))

        for idx in need:
            await send_msg(writer, {"type": "request", "index": idx})
            msg = await recv_msg(reader)

            if msg and msg.get("type") == "piece" and msg.get("index") == idx:
                data = base64.b64decode(msg["dataB64"])
                ok = self.store.write_piece(idx, data)
                if not ok:
                    log.warning("[client] hash mismatch on piece %s", idx)
            else:
                log.warning("[client] unexpected msg for piece %s: %s", idx, msg)

        writer.close()

        if self.store.is_complete():
            out = self.store.finalize()
            if out:
                log.info("[client] download complete → %s", out)
        else:
            missing = total - len(self.store.have)
            log.warning("[client] incomplete, missing %s pieces", missing)

    # ---------------- parallel worker ----------------
    async def _worker(self, host: str, port: int, q: asyncio.Queue) -> None:
        """
        Worker: grabs piece indices from queue and downloads them.
        """
        reader, writer = await asyncio.open_connection(host, port)
        await self._handshake_and_bitfield(reader, writer)

        try:
            while True:
                idx = q.get_nowait()
                await send_msg(writer, {"type": "request", "index": idx})
                msg = await recv_msg(reader)

                if msg and msg.get("type") == "piece" and msg.get("index") == idx:
                    data = base64.b64decode(msg["dataB64"])
                    async with self._write_lock:
                        ok = self.store.write_piece(idx, data)
                        if not ok:
                            log.warning("[client] hash mismatch on piece %s", idx)
                else:
                    log.warning("[client] unexpected msg (worker) for %s: %s", idx, msg)

                q.task_done()
        except asyncio.QueueEmpty:
            pass
        finally:
            writer.close()

    # ---------------- parallel download ----------------
    async def download_from_parallel(self, host: str, port: int, workers: int = 3) -> None:
        """
        Open N connections to the same peer and split pieces across workers.
        """
        total = len(self.meta["pieces"])
        need = sorted(set(range(total)) - self.store.have)

        if not need:
            out = self.store.finalize()
            if out:
                log.info("[client] already complete → %s", out)
            return

        log.info("[client] requesting %s pieces with %s workers", len(need), workers)

        q: asyncio.Queue[int] = asyncio.Queue()
        for idx in need:
            q.put_nowait(idx)

        n = min(workers, len(need))
        tasks = [asyncio.create_task(self._worker(host, port, q)) for _ in range(n)]
        await asyncio.gather(*tasks)

        if self.store.is_complete():
            out = self.store.finalize()
            if out:
                log.info("[client] download complete → %s", out)
