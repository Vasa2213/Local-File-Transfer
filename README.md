# Local-File-Transfer
File Transfer Server Upto 5GB
Over Same Wifi

#!/usr/bin/env python3
"""
Local Media Transfer Server
============================
Transfer photos, videos, and other files (up to 5 GB each) between your
Windows PC and your iPhone/iPad over your local WiFi network.
No internet connection, cables, or cloud storage required.

SETUP (on Windows):
    pip install flask

RUN (on Windows):
    python media_transfer_server.py

THEN, ON YOUR IPHONE:
    1. Make sure the iPhone is on the SAME WiFi network as the PC.
    2. Open Safari and go to the address printed in the terminal,
       e.g.  http://192.168.1.23:5000
    3. Use the page to upload photos/videos from your phone, or download
       files that are sitting in the shared folder on your PC.

NOTES:
    - Files land in a "shared_files" folder next to this script.
    - Windows Firewall may prompt you the first time you run this --
      click "Allow access" (at least for Private networks).
    - This is meant for trusted home/local-network use only; it has no
      login and is not encrypted (plain HTTP), which is fine on your own
      WiFi but don't expose it to the open internet.
"""
