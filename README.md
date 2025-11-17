🌐 Mini BitTorrent-Style P2P File Sharing System

A lightweight, fully-functional peer-to-peer (P2P) file sharing system built in Python, inspired by the core ideas of the BitTorrent protocol — file chunking, hashing, piece verification, resumable downloads, multi-connection parallelism, and tracker-based peer discovery.

This project demonstrates how computers can share files directly without any central server.

Highlights

Feature	Description

🔹 File chunking	Splits files into equal-sized pieces (default 1 MB)

🔹 SHA-256 hashing	Ensures integrity and prevents corrupted pieces

🔹 Resumable downloads	State is saved as .state.json so you can resume anytime

🔹 Parallel downloads	Multiple TCP connections for faster transfer

🔹 Tracker support	Peers can discover each other without manual IP

🔹 Clean Python-only implementation	No external libraries — 100% standard library

🔹 Simple CLI commands	Create metadata, seed, download
