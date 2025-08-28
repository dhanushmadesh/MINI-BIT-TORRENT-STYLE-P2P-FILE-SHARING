import asyncio, base64
from .wire import send_msg, recv_msg

class PeerServer:
    """
    Minimal peer server:
    - expects a client handshake with matching infoHash
    - replies handshake + bitfield
    - serves requested pieces
    """
    def __init__(self, host, port, meta, store, peer_id: str):
        self.host, self.port = host, port
        self.meta, self.store, self.peer_id = meta, store, peer_id

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        # 1) Expect client's handshake first
        try:
            hello = await recv_msg(reader)
        except Exception:
            writer.close(); return
        if not hello or hello.get("type") != "handshake" or hello.get("infoHash") != self.meta["infoHash"]:
            writer.close(); return

        # 2) Reply handshake + bitfield
        await send_msg(writer, {"type":"handshake","infoHash":self.meta["infoHash"],"peerId":self.peer_id})
        await send_msg(writer, {"type":"bitfield","have":sorted(self.store.have),"totalPieces":len(self.meta["pieces"])})

        # 3) Serve requests
        try:
            while True:
                msg = await recv_msg(reader)
                if not msg: break
                if msg.get("type") == "request":
                    idx = int(msg["index"])
                    data = self.store.read_piece(idx)
                    if data is not None:
                        await send_msg(writer, {
                            "type":"piece",
                            "index": idx,
                            "dataB64": base64.b64encode(data).decode()
                        })
        except Exception:
            pass
        writer.close()

    async def serve(self):
        server = await asyncio.start_server(self._handle, self.host, self.port)
        print(f"[server] Listening on {self.host}:{self.port}")
        async with server:
            await server.serve_forever()
