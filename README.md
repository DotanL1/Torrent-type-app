# Torrent-type-app
🔗 BitTorrent-Style P2P File Sharing App

A hybrid client-server + peer-to-peer (P2P) file sharing system that enables efficient, secure, and parallel file distribution between peers.

This project implements core BitTorrent concepts from scratch, including chunk-based file transfer, peer discovery via a tracker, and encrypted communication between nodes.

🚀 Features
Hybrid Architecture
Central tracker for peer discovery
Direct peer-to-peer file transfers
Chunk-Based Downloading
Files are split into chunks
Parallel downloading from multiple peers
Automatic file reconstruction
Secure Communication
Diffie-Hellman key exchange
AES encryption for data transfer
RSA support for secure operations
Peer-to-Peer Networking
Each client runs its own TCP server
Handles incoming chunk requests from other peers
Smart Download Flow
User confirmation before download
Dynamic chunk requests from available peers
Networking Enhancements
UPnP support for port forwarding
Public IP detection
GUI Interface
Built with wxPython
Interactive file selection and transfer management
🧠 What This Project Demonstrates
Understanding of distributed systems & P2P protocols
Implementation of network communication over TCP
Practical use of cryptography (DH, RSA, AES)
Handling concurrency and parallel downloads
Designing scalable file transfer logic
🛠️ Tech Stack
Python
wxPython (GUI)
Socket Programming (TCP)
Cryptography (Diffie-Hellman, RSA, AES)
UPnP (miniupnpc)
