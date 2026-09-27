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

import os
import socket
from pathlib import Path

from flask import (
    Flask, request, render_template_string, send_from_directory,
    redirect, url_for, flash, get_flashed_messages
)
from werkzeug.utils import secure_filename

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PORT = 5000
SHARE_FOLDER = Path(__file__).resolve().parent / "shared_files"
MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024  # 5 GB, per upload

SHARE_FOLDER.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE
app.secret_key = "local-media-transfer"  # only used to sign flash messages

# ---------------------------------------------------------------------------
# HTML (kept inline so this stays a single portable file)
# ---------------------------------------------------------------------------
PAGE = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Media Transfer</title>
<style>
  body { font-family: -apple-system, system-ui, sans-serif; background:#f4f5f7; margin:0; padding:16px; color:#1d1d1f; }
  h1 { font-size: 1.3rem; margin-bottom: 4px; }
  .sub { color:#666; font-size:0.85rem; margin-bottom:18px; }
  .card { background:#fff; border-radius:12px; padding:16px; margin-bottom:16px; box-shadow:0 1px 3px rgba(0,0,0,0.08); }
  .flash { background:#e8f8ee; border:1px solid #34c759; color:#1c6b34; padding:10px 12px; border-radius:8px; margin-bottom:12px; font-size:0.9rem; }
  input[type=file] { width:100%; padding:10px 0; }
  button { background:#007aff; color:#fff; border:none; padding:12px 18px; border-radius:8px; font-size:1rem; width:100%; margin-top:8px; }
  button:disabled { background:#a9c9f5; }
  progress { width:100%; height:14px; margin-top:10px; border-radius:8px; overflow:hidden; }
  ul { list-style:none; padding:0; margin:0; }
  li { display:flex; justify-content:space-between; align-items:center; padding:10px 0; border-bottom:1px solid #eee; }
  li:last-child { border-bottom:none; }
  .fname { font-size:0.92rem; word-break:break-all; padding-right:8px; }
  .fsize { color:#888; font-size:0.8rem; white-space:nowrap; }
  .actions a, .actions button.small { font-size:0.85rem; padding:6px 10px; border-radius:6px; margin-left:6px; width:auto; }
  a.download { background:#34c759; color:#fff; text-decoration:none; }
  button.delete { background:#ff3b30; }
  .empty { color:#888; font-size:0.9rem; text-align:center; padding:20px 0; }
  #status { font-size:0.85rem; color:#555; margin-top:6px; }
</style>
</head>
<body>
  <h1>Media Transfer</h1>
  <div class="sub">Up to {{ max_gb }} GB per file &middot; same-WiFi transfer, no cloud</div>

  {% for msg in get_flashed_messages() %}
    <div class="flash">{{ msg }}</div>
  {% endfor %}

  <div class="card">
    <form id="uploadForm">
      <input type="file" id="fileInput" multiple>
      <button type="submit" id="uploadBtn">Upload to PC</button>
      <progress id="progressBar" value="0" max="100" style="display:none;"></progress>
      <div id="status"></div>
    </form>
  </div>

  <div class="card">
    <ul>
      {% for f in files %}
        <li>
          <div class="fname">{{ f.name }}<div class="fsize">{{ f.size }}</div></div>
          <div class="actions">
            <a class="download" href="{{ url_for('download', filename=f.name) }}">Download</a>
            <form style="display:inline" method="post" action="{{ url_for('delete', filename=f.name) }}"
                  onsubmit="return confirm('Delete {{ f.name }}?');">
              <button type="submit" class="delete small">Delete</button>
            </form>
          </div>
        </li>
      {% else %}
        <div class="empty">No files yet. Upload something from your phone.</div>
      {% endfor %}
    </ul>
  </div>

<script>
const form = document.getElementById('uploadForm');
const input = document.getElementById('fileInput');
const bar = document.getElementById('progressBar');
const status = document.getElementById('status');
const btn = document.getElementById('uploadBtn');

form.addEventListener('submit', function (e) {
  e.preventDefault();
  const files = Array.from(input.files);
  if (files.length === 0) return;
  btn.disabled = true;
  bar.style.display = 'block';
  uploadNext(files, 0);
});

function uploadNext(files, i) {
  if (i >= files.length) {
    status.textContent = 'Done. Refreshing...';
    setTimeout(() => location.reload(), 500);
    return;
  }
  const file = files[i];
  status.textContent = `Uploading ${file.name} (${i + 1}/${files.length})...`;
  const data = new FormData();
  data.append('file', file);

  const xhr = new XMLHttpRequest();
  xhr.open('POST', '/upload');
  xhr.upload.onprogress = function (evt) {
    if (evt.lengthComputable) {
      bar.value = (evt.loaded / evt.total) * 100;
    }
  };
  xhr.onload = function () {
    uploadNext(files, i + 1);
  };
  xhr.onerror = function () {
    status.textContent = `Failed to upload ${file.name}. Check WiFi and try again.`;
    btn.disabled = false;
  };
  xhr.send(data);
}
</script>
</body>
</html>
"""


def human_size(num_bytes):
    num = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if num < 1024:
            return f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} TB"


@app.route("/")
def index():
    files = []
    for p in sorted(SHARE_FOLDER.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.is_file():
            files.append({"name": p.name, "size": human_size(p.stat().st_size)})
    return render_template_string(PAGE, files=files, max_gb=MAX_FILE_SIZE // (1024 ** 3))


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        flash("No file received.")
        return redirect(url_for("index"))
    f = request.files["file"]
    if f.filename == "":
        flash("No file selected.")
        return redirect(url_for("index"))

    filename = secure_filename(f.filename) or "upload.bin"
    dest = SHARE_FOLDER / filename
    stem, suffix = dest.stem, dest.suffix
    counter = 1
    while dest.exists():
        dest = SHARE_FOLDER / f"{stem}_{counter}{suffix}"
        counter += 1

    f.save(dest)  # streamed to disk by Werkzeug, safe for multi-GB files
    flash(f"Uploaded {dest.name} ({human_size(dest.stat().st_size)})")
    return redirect(url_for("index"))


@app.route("/download/<path:filename>")
def download(filename):
    return send_from_directory(SHARE_FOLDER, filename, as_attachment=True)


@app.route("/delete/<path:filename>", methods=["POST"])
def delete(filename):
    target = SHARE_FOLDER / secure_filename(filename)
    if target.exists() and target.is_file():
        target.unlink()
        flash(f"Deleted {filename}")
    return redirect(url_for("index"))


@app.errorhandler(413)
def too_large(e):
    flash(f"File too large. Max size is {MAX_FILE_SIZE // (1024 ** 3)} GB.")
    return redirect(url_for("index"))


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))  # no data sent, just used to pick the right interface
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


if __name__ == "__main__":
    ip = get_local_ip()
    print("=" * 60)
    print(" Local Media Transfer Server")
    print("=" * 60)
    print(f" Shared folder : {SHARE_FOLDER}")
    print(f" Max file size : {MAX_FILE_SIZE // (1024 ** 3)} GB")
    print(f" On your iPhone (same WiFi), open Safari and go to:")
    print(f"     http://{ip}:{PORT}")
    print("=" * 60)
    app.run(host="0.0.0.0", port=PORT, threaded=True)
