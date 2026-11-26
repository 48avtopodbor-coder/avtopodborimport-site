#!/usr/bin/env python3
"""Serve original Che168 photos through the existing collector host, caching by URL."""

import hashlib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import subprocess
import threading
import time
from urllib.parse import parse_qs, urlsplit

CACHE = Path("/opt/avtopodborimport/photo-cache")
CACHE_LIMIT_BYTES = 1_000_000_000
CACHE_KEY_RE = re.compile(r"[0-9a-f]{64}")
DISK_RESERVE_BYTES = 4 * 1024**3
SLOTS = threading.BoundedSemaphore(2)
MASTER_LOCK = threading.Lock()
SSH_SOCKET = "/run/avto-photo-relay-ssh"
CONNECT_AFTER = 0.0
BRIDGE_STATE = Path("/srv/che168/pc-bridge")


class PhotoCache:
    def __init__(self, directory, limit):
        self.directory = directory
        self.limit = limit
        self.lock = threading.Lock()
        directory.mkdir(parents=True, exist_ok=True)
        self.block_size = os.statvfs(directory).f_frsize
        self.used = self.trim(limit)

    def trim(self, limit):
        entries = []
        with os.scandir(self.directory) as files:
            for entry in files:
                if not CACHE_KEY_RE.fullmatch(entry.name):
                    continue
                try:
                    info = entry.stat(follow_symlinks=False)
                except FileNotFoundError:
                    continue
                if stat.S_ISREG(info.st_mode):
                    entries.append((info.st_mtime_ns, entry.path, info.st_blocks * 512))
        used = sum(size for _, _, size in entries)
        if used <= limit:
            return used
        for _, path, size in sorted(entries):
            Path(path).unlink(missing_ok=True)
            used -= size
            if used <= limit:
                break
        return used

    def read(self, key):
        try:
            with (self.directory / key).open("rb") as photo:
                body = photo.read()
                try:
                    os.utime(photo.fileno(), None)
                except OSError:
                    pass
                return body
        except FileNotFoundError:
            return None

    def store(self, key, body):
        blocks = (len(body) + self.block_size - 1) // self.block_size
        required = blocks * self.block_size
        if required > self.limit:
            return
        target = self.directory / key
        with self.lock:
            if target.exists():
                return
            if self.used + required > self.limit:
                self.used = self.trim(min(self.limit - required, self.limit * 9 // 10))
            if shutil.disk_usage(self.directory).free < DISK_RESERVE_BYTES + required:
                return
            temporary = target.with_suffix(f".{threading.get_ident()}.tmp")
            try:
                temporary.write_bytes(body)
                allocated = temporary.stat().st_blocks * 512
                if self.used + allocated > self.limit:
                    return
                temporary.replace(target)
                self.used += allocated
            finally:
                temporary.unlink(missing_ok=True)

    def refresh(self):
        """Account for files written by the optional workstation bridge."""
        with self.lock:
            self.used = self.trim(self.limit)


def workstation_alive():
    if (BRIDGE_STATE / "disabled").exists():
        return False
    try:
        return time.time() - (BRIDGE_STATE / "alive").stat().st_mtime < 120
    except OSError:
        return False


def enqueue_workstation(url, key):
    if (BRIDGE_STATE / "disabled").exists():
        return
    pending = BRIDGE_STATE / "pending"
    pending.mkdir(parents=True, exist_ok=True)
    temporary = pending / (key + "." + str(threading.get_ident()) + ".tmp")
    temporary.write_text(json.dumps({"url": url}))
    temporary.replace(pending / (key + ".json"))


def ensure_master():
    """Reuse one authenticated TCP connection and back off when hosting is unavailable."""
    global CONNECT_AFTER
    with MASTER_LOCK:
        if time.monotonic() < CONNECT_AFTER:
            return False
        check = subprocess.run(
            ["ssh", "-S", SSH_SOCKET, "-O", "check", "hosting"],
            capture_output=True,
            timeout=3,
        )
        if check.returncode == 0:
            return True
        Path(SSH_SOCKET).unlink(missing_ok=True)
        try:
            master = subprocess.run(
                [
                    "ssh",
                    "-M",
                    "-N",
                    "-f",
                    "-S",
                    SSH_SOCKET,
                    "-o",
                    "BatchMode=yes",
                    "-o",
                    "ConnectTimeout=8",
                    "-o",
                    "ControlPersist=600",
                    "-o",
                    "ServerAliveInterval=30",
                    "-o",
                    "ServerAliveCountMax=2",
                    "hosting",
                ],
                capture_output=True,
                timeout=12,
            )
        except (subprocess.TimeoutExpired, OSError):
            CONNECT_AFTER = time.monotonic() + 120
            return False
        if master.returncode:
            CONNECT_AFTER = time.monotonic() + 120
            return False
        return True


REMOTE = """import http.client,sys
from urllib.parse import urlsplit
u=urlsplit(sys.stdin.read()); c=http.client.HTTPSConnection(u.hostname,timeout=20)
c.request("GET",u.path+("?"+u.query if u.query else ""),headers={"User-Agent":"Mozilla/5.0","Accept":"image/webp,image/*;q=0.8"})
r=c.getresponse(); b=r.read()
if r.status!=200 or not (r.getheader("Content-Type") or "").startswith("image/"): sys.exit(1)
sys.stdout.buffer.write(b)
"""


def allowed(url):
    try:
        u = urlsplit(url)
        return (
            u.scheme == "https"
            and not u.username
            and not u.password
            and u.port in (None, 443)
            and bool(u.hostname)
            and (u.hostname == "autoimg.cn" or u.hostname.endswith(".autoimg.cn"))
        )
    except ValueError:
        return False


def image_type(body):
    if body.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if body.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if body.startswith(b"RIFF") and body[8:12] == b"WEBP":
        return "image/webp"
    if body.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    return None


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = parse_qs(urlsplit(self.path).query).get("url", [""])[0]
        if urlsplit(self.path).path != "/api/img" or not allowed(url):
            self.send_error(400)
            return
        key = hashlib.sha256(url.encode()).hexdigest()
        cache = self.server.photo_cache
        body = cache.read(key)
        if body is None:
            enqueue_workstation(url, key)
            if workstation_alive():
                deadline = time.monotonic() + 45
                while body is None and time.monotonic() < deadline:
                    body = cache.read(key)
                    if body is not None:
                        cache.refresh()
                        break
                    time.sleep(0.2)
                if body is None:
                    self.send_response(503)
                    self.send_header("Retry-After", "30")
                    self.end_headers()
                    return
            if body is not None:
                return self.serve_photo(body)
            if not SLOTS.acquire(timeout=20):
                self.send_error(503)
                return
            try:
                body = cache.read(key)
                if body is None:
                    if not ensure_master():
                        self.send_response(503)
                        self.send_header("Retry-After", "120")
                        self.end_headers()
                        return
                    result = subprocess.run(
                        [
                            "ssh",
                            "-S",
                            SSH_SOCKET,
                            "-o",
                            "ControlMaster=no",
                            "-o",
                            "ProxyCommand=false",
                            "-o",
                            "BatchMode=yes",
                            "-o",
                            "ConnectTimeout=8",
                            "hosting",
                            "python3 -c " + shlex.quote(REMOTE),
                        ],
                        input=url.encode(),
                        capture_output=True,
                        timeout=30,
                    )
                    if result.returncode or not image_type(result.stdout):
                        self.send_error(502)
                        return
                    body = result.stdout
                    try:
                        cache.store(key, body)
                    except OSError as error:
                        self.log_error("Photo cache write failed: %s", error)
            except (subprocess.TimeoutExpired, OSError):
                self.send_error(502)
                return
            finally:
                SLOTS.release()
        self.serve_photo(body)

    def serve_photo(self, body):
        try:
            ctype = image_type(body)
            if not ctype:
                self.send_error(502)
                return
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "public, max-age=86400")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass


if __name__ == "__main__":
    photo_cache = PhotoCache(CACHE, CACHE_LIMIT_BYTES)
    with ThreadingHTTPServer(("127.0.0.1", 3011), Handler) as server:
        server.photo_cache = photo_cache
        server.serve_forever()
