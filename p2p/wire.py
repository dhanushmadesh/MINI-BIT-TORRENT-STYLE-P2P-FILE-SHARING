import asyncio, json, struct

def _pack(obj: dict) -> bytes:
    b = json.dumps(obj, separators=(',', ':')).encode()
    return struct.pack(">I", len(b)) + b

async def send_msg(writer: asyncio.StreamWriter, obj: dict):
    writer.write(_pack(obj))
    await writer.drain()

async def recv_msg(reader: asyncio.StreamReader) -> dict | None:
    # raises asyncio.IncompleteReadError if peer disconnects mid-frame
    hdr = await reader.readexactly(4)
    (n,) = struct.unpack(">I", hdr)
    data = await reader.readexactly(n)
    return json.loads(data.decode())
