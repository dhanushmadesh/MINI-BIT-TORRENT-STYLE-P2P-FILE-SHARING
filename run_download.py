import asyncio, random, string
from pathlib import Path
from p2p.meta import read_meta
from p2p.pieces import PieceStore
from p2p.peer_client import PeerClient

def peer_id(n=20):
    import random, string
    return ''.join(random.choice(string.ascii_letters+string.digits) for _ in range(n))

async def main():
    meta = read_meta(r'samples\file.bin.p2pmeta')
    store = PieceStore(meta, Path(r'.\downloads'))
    cli = PeerClient(meta, store, peer_id())
    await cli.download_from('127.0.0.1', 5001)

if __name__ == "__main__":
    asyncio.run(main())
