📂 Mini P2P File Sharing System

A lightweight BitTorrent-style peer-to-peer (P2P) file sharing system built in Python using only the standard library.

This project demonstrates how files can be shared directly between machines without a central server — using file chunking, piece verification, resumable transfers, parallel connections, and optional tracker-based peer discovery.

🚀 Features

✅ File chunking with SHA-256 for integrity

✅ Unique .p2pmeta metadata files (like .torrent)

✅ Seeder & downloader entry scripts (run_seed.py, run_download.py)

✅ Resume support (.state.json keeps track of progress)

✅ Sequential or parallel downloads (faster transfer with multiple connections)

✅ Optional tracker for peer discovery

✅ Cross-platform (Windows/Linux/Mac)

✅ Pure Python — no external dependencies

📦 Folder Structure
p2p-share/
│
├── p2p/                   # Core library
│   ├── meta.py            # Build/read metadata (.p2pmeta)
│   ├── pieces.py          # Piece storage & state handling
│   ├── wire.py            # Length-prefixed JSON wire protocol
│   ├── peer_server.py     # Seeder (serves pieces to clients)
│   ├── peer_client.py     # Downloader (sequential + parallel)
│   ├── cli.py             # Unified CLI (create / seed / download)
│   └── tracker.py         # Optional HTTP tracker for peer discovery
│
├── run_seed.py            # Simple entry script to seed a file
├── run_download.py        # Simple entry script to download a file
├── samples/               # Sample source files + generated .p2pmeta
├── data/                  # Seeder’s working directory
├── downloads/             # Downloader’s output directory
└── README.md              # Project documentation

📂 Folder Purpose (detailed)

samples/

Contains original files you want to share.

Example: samples/demo.txt.

When you run create, it generates samples/demo.txt.p2pmeta.

data/ (Seeder’s working folder)

Created by seeder (run_seed.py).

Stores:

<file>.partial – reconstructed file in piece format

<file>.state.json – list of which pieces the seeder has

Even if the original file is deleted, the seeder can still seed from data/.

downloads/ (Downloader’s folder)

Created by downloader (run_download.py).

Stores:

<file>.partial – temporary file during download

<file>.state.json – progress tracking

<file> – final completed file once all pieces are downloaded

🛠️ Installation

Clone this repository:

git clone https://github.com/<your-username>/p2p-share.git
cd p2p-share


Ensure Python 3.9+ is installed.
Check with:

python --version

🔹 Usage Guide
1. Create Metadata

Generate a .p2pmeta file describing your original file:

python -m p2p.cli create samples/demo.txt


Output:

samples/demo.txt.p2pmeta

2. Start Seeding (PC with the original file)
python run_seed.py --meta samples/demo.txt.p2pmeta --source samples/demo.txt --port 5001 --workdir ./data


Example log:

[seed] ingested 5/5 verified pieces from samples/demo.txt
[seed] serving demo.txt (pieces=5) on 192.168.1.20:5001
[seed] hint: on downloader → python run_download.py --meta samples/demo.txt.p2pmeta --host 192.168.1.20 --port 5001

3. Start Downloading (other machine)

Copy samples/demo.txt.p2pmeta to the downloader machine.
Then run:

python run_download.py --meta samples/demo.txt.p2pmeta --host 192.168.1.20 --port 5001 --workdir ./downloads --parallel 3


Output:

[client] requesting 5 pieces with 3 workers
[client] download complete → downloads/demo.txt

4. Verify File

On Windows (PowerShell):

fc.exe samples\demo.txt downloads\demo.txt


On Linux/Mac:

diff samples/demo.txt downloads/demo.txt


✅ No differences → files are identical.

5. (Optional) Use Tracker

Run tracker:

python -m p2p.tracker --port 7000


Seeder with tracker:

python run_seed.py --meta samples/demo.txt.p2pmeta --source samples/demo.txt --port 5001 --tracker 127.0.0.1:7000


Downloader with tracker:

python run_download.py --meta samples/demo.txt.p2pmeta --tracker 127.0.0.1:7000 --workdir ./downloads


Tracker auto-shares seeder IP/port → no manual entry needed.

🔍 Example: Testing on One Machine

Terminal 1 (Seeder):

python run_seed.py --meta samples/demo.txt.p2pmeta --source samples/demo.txt --port 5001


Terminal 2 (Downloader):

python run_download.py --meta samples/demo.txt.p2pmeta --host 127.0.0.1 --port 5001 --workdir ./downloads


Verify with fc.exe or diff.

🌟 Future Enhancements

Multi-peer piece exchange (swarm downloads, true P2P)

Encrypted/TLS transport

Multi-file torrents

Rate limiting / fairness

Web interface for monitoring progress

📚 Educational Value

This project re-implements the fundamentals of BitTorrent in under 1000 lines of Python, making it ideal for learning about:

Distributed systems

Networking protocols

Asynchronous I/O (asyncio)

File integrity and hashing

Resume-capable downloads

It’s both a portfolio project and a learning resource.

🙌 Author

Dhanush Madesh (and contributors)
