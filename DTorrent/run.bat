echo Starting Tracker Server...
cd tracker
start "Tracker Server" py tracker_server.py
cd ..

echo Starting Peer Client...
cd peer
start "Peer Client" py peer_client.py
start "Peer Client" py peer_client.py
start "Peer Client" py peer_client.py


cd ..

