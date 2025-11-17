📂 Mini P2P File Sharing System

A lightweight BitTorrent-style peer-to-peer (P2P) file sharing system built in Python using only the standard library.

This project demonstrates how files can be shared directly between machines without a central server — using file chunking, piece verification, resumable transfers, parallel connections, and optional tracker-based peer discovery.

 Features

✅ File chunking with SHA-256 for integrity

✅ Unique .p2pmeta metadata files (like .torrent)

✅ Seeder & downloader entry scripts (run_seed.py, run_download.py)

✅ Resume support (.state.json keeps track of progress)

✅ Sequential or parallel downloads (faster transfer with multiple connections)

✅ Optional tracker for peer discovery

✅ Cross-platform (Windows/Linux/Mac)

✅ Pure Python — no external dependencies



