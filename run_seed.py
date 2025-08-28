import asyncio, random, string
from pathlib import Path
from p2p.meta import read_meta
from p2p.pieces import PieceStore
from p2p.peer_server import PeerServer

def peer_id(n=20):
    return ''.join(random.choice(string.ascii_letters+string.digits) for _ in range(n))

async def main():
    # EDIT 1: point to your PDF's .p2pmeta
    meta = read_meta(r'samples\7TH SEM SYLLABUS.pdf.p2pmeta')
    store = PieceStore(meta, Path(r'.\data'))
    # EDIT 2: ingest from your actual source file (uncommented)
    store.ingest_from_source(r'samples\7TH SEM SYLLABUS.pdf')
    srv = PeerServer("0.0.0.0", 5001, meta, store, peer_id())
    await srv.serve()

if __name__ == "__main__":
    asyncio.run(main())
