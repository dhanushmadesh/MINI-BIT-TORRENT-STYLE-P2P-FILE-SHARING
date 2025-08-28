import asyncio, base64
from .wire import send_msg, recv_msg

class PeerClient:
    """
    Supports single-connection (sequential) and multi-connection (parallel) downloads.
    Parallel mode opens N TCP connections to the same peer and splits pieces across workers.
    """
    def __init__(self, meta, store, peer_id: str):
        self.meta, self.store, self.peer_id = meta, store, peer_id
        self._write_lock = asyncio.Lock()  # protect writes to .partial

    async def _handshake_and_bitfield(self, reader, writer):
        await send_msg(writer, {"type":"handshake","infoHash":self.meta["infoHash"],"peerId":self.peer_id})
        hs = await recv_msg(reader)
        bf = await recv_msg(reader)
        if not hs or hs.get("type")!="handshake" or hs.get("infoHash")!=self.meta["infoHash"]:
            writer.close(); raise RuntimeError("Handshake failed")
        return bf

    async def download_from(self, host: str, port: int):
        """Single connection, sequential requests (baseline)."""
        reader, writer = await asyncio.open_connection(host, port)
        await self._handshake_and_bitfield(reader, writer)

        total = len(self.meta["pieces"])
        need = sorted(set(range(total)) - self.store.have)
        for idx in need:
            await send_msg(writer, {"type":"request","index": idx})
            msg = await recv_msg(reader)
            if msg and msg.get("type")=="piece" and msg.get("index")==idx:
                data = base64.b64decode(msg["dataB64"])
                ok = self.store.write_piece(idx, data)
                if not ok:
                    print(f"[client] Hash mismatch on piece {idx}")
            else:
                print(f"[client] Unexpected msg: {msg}")
        writer.close()
        if self.store.is_complete():
            out = self.store.finalize()
            if out: print(f"[client] Download complete → {out}")
        else:
            missing = total - len(self.store.have)
            print(f"[client] Incomplete, missing {missing} pieces.")

    async def _worker(self, host: str, port: int, q: asyncio.Queue):
        reader, writer = await asyncio.open_connection(host, port)
        await self._handshake_and_bitfield(reader, writer)
        try:
            while True:
                idx = q.get_nowait()
                await send_msg(writer, {"type":"request","index": idx})
                msg = await recv_msg(reader)
                if msg and msg.get("type")=="piece" and msg.get("index")==idx:
                    data = base64.b64decode(msg["dataB64"])
                    async with self._write_lock:
                        ok = self.store.write_piece(idx, data)
                        if not ok:
                            print(f"[client] Hash mismatch on piece {idx}")
                else:
                    print(f"[client] Unexpected msg (worker): {msg}")
                q.task_done()
        except asyncio.QueueEmpty:
            pass
        finally:
            writer.close()

    async def download_from_parallel(self, host: str, port: int, workers: int = 3):
        """Open N connections to the same peer and split pieces across workers."""
        total = len(self.meta["pieces"])
        need = sorted(set(range(total)) - self.store.have)
        if not need:
            out = self.store.finalize()
            if out: print(f"[client] Already complete → {out}")
            return
        q = asyncio.Queue()
        for idx in need:
            q.put_nowait(idx)
        n = min(workers, len(need))
        tasks = [asyncio.create_task(self._worker(host, port, q)) for _ in range(n)]
        await asyncio.gather(*tasks)
        if self.store.is_complete():
            out = self.store.finalize()
            if out: print(f"[client] Download complete → {out}")
