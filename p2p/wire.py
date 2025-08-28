# p2p/wire.py
from __future__ import annotations

import asyncio
import json
import struct
from typing import Any, Dict, Optional


HEADER_STRUCT = struct.Struct(">I")  # 4-byte big-endian length prefix


def _pack(obj: Dict[str, Any]) -> bytes:
    """
    Serialize a dict to length-prefixed JSON bytes.

    Wire format:
        [4-byte length prefix][JSON payload]

    Args:
        obj: JSON-serializable dictionary.

    Returns:
        Bytes ready to send over a TCP stream.
    """
    try:
        b = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    except Exception as e:
        raise ValueError(f"Failed to encode JSON message: {e}") from e
    return HEADER_STRUCT.pack(len(b)) + b


async def send_msg(writer: asyncio.StreamWriter, obj: Dict[str, Any]) -> None:
    """
    Send a single JSON message with length prefix.

    Args:
        writer: asyncio StreamWriter.
        obj: Dictionary to send.
    """
    writer.write(_pack(obj))
    await writer.drain()


async def recv_msg(reader: asyncio.StreamReader) -> Optional[Dict[str, Any]]:
    """
    Receive one JSON message from the stream.

    Raises asyncio.IncompleteReadError if the peer disconnects mid-frame.

    Args:
        reader: asyncio StreamReader.

    Returns:
        Decoded dictionary, or None if EOF.
    """
    try:
        hdr = await reader.readexactly(4)
    except asyncio.IncompleteReadError:
        return None

    (n,) = HEADER_STRUCT.unpack(hdr)
    try:
        data = await reader.readexactly(n)
    except asyncio.IncompleteReadError:
        return None

    try:
        return json.loads(data.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON received: {e}") from e
