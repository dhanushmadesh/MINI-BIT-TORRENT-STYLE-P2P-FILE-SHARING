# p2p/peer_server.py
from __future__ import annotations

import asyncio
import base64
import logging
from typing import Dict

from .wire import send_msg, recv_msg

log = logging.getLogger(__name__)


class PeerServer:
    """
    Minimal peer server:
    - expects a client handshake with matching infoHash
    - replies with handshake + bitfield
    - serves requested pieces on demand
    """

    def __init__(self, host: str, port: int, meta: Dict, store, peer_id: str):
        self.host = host
        self.port = port
        self.meta = meta
        self.store = store
        self.peer_id = peer_id

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """
        Handle a single peer connection:
        - validate handshake
        - send handshake + bitfield
        - serve request/piece loop
        """
        peer_addr = writer.get_extra_info("peername")
        try:
            # 1) Expect client's handshake first
            hello = await recv_msg(reader)
        except Exception as e:
            log.warning("[server] handshake read failed from %s: %s", peer_addr, e)
            writer.close()
            return

        if (
            not hello
            or hello.get("type") != "handshake"
            or hello.get("infoHash") != self.meta["infoHash"]
        ):
            log.warning("[server] invalid handshake from %s: %s", peer_addr, hello)
            writer.close()
            return

        # 2) Reply handshake + bitfield
        await send_msg(
            writer,
            {"type": "handshake", "infoHash": self.meta["infoHash"], "peerId": self.peer_id},
        )
        await send_msg(
            writer,
            {"type": "bitfield", "have": sorted(self.store.have), "totalPieces": len(self.meta["pieces"])},
        )
        log.info("[server] handshake ok with %s", peer_addr)

        # 3) Serve requests
        try:
            while True:
                msg = await recv_msg(reader)
                if not msg:
                    break
                if msg.get("type") == "request":
                    idx = int(msg["index"])
                    data = self.store.read_piece(idx)
                    if data is not None:
                        await send_msg(
                            writer,
                            {
                                "type": "piece",
                                "index": idx,
                                "dataB64": base64.b64encode(data).decode("utf-8"),
                            },
                        )
                        log.debug("[server] sent piece %s to %s", idx, peer_addr)
        except Exception as e:
            log.warning("[server] error serving %s: %s", peer_addr, e)
        finally:
            writer.close()
            log.info("[server] closed connection to %s", peer_addr)

    async def serve(self) -> None:
        """
        Start serving peers on host:port until cancelled.
        """
        server = await asyncio.start_server(self._handle, self.host, self.port)
        log.info("[server] listening on %s:%s", self.host, self.port)
        async with server:
            await server.serve_forever()
