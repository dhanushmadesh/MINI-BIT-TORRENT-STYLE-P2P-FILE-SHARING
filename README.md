\# Mini BitTorrent-style P2P (Python asyncio)



A learning project that implements a BitTorrent-like peer:

\- \*\*Chunking\*\* with per-piece \*\*SHA-256\*\* integrity

\- \*\*Custom wire protocol\*\* (length-prefixed JSON over TCP)

\- \*\*Seeder\*\* and \*\*downloader\*\* CLI

\- \*\*Parallel downloads\*\* (`--parallel N`)

\- \*\*Tracker-based peer discovery\*\* (tiny HTTP tracker)

\- \*\*Resume support\*\* (persists piece bitmap to `.state.json`)



\## Quickstart (3 terminals)



\*\*Terminal C – Tracker\*\*

```bash

python -m p2p.tracker --port 7000



