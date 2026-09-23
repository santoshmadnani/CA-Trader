#!/usr/bin/env python3
"""
server_host/install_host_prerequisites.py
Automated setup script for hosting CA Trader on any Windows laptop.
1. Validates Python environment.
2. Creates required directories (bin, logs, backups).
3. Downloads the official standalone cloudflared.exe binary (no admin rights required).
4. Verifies database and core application dependencies.
"""

import sys
import os
import shutil
import urllib.request
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
HOST_DIR = BASE_DIR / "server_host"
BIN_DIR = HOST_DIR / "bin"
LOGS_DIR = HOST_DIR / "logs"
BACKUPS_DIR = HOST_DIR / "backups"
CLOUDFLARED_EXE = BIN_DIR / "cloudflared.exe"

CLOUDFLARED_URL = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"

def ensure_directories():
    print("[1/4] Creating server directories...", flush=True)
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  + bin:     {BIN_DIR}")
    print(f"  + logs:    {LOGS_DIR}")
    print(f"  + backups: {BACKUPS_DIR}")

def install_dependencies():
    print("\n[2/4] Verifying Python dependencies...", flush=True)
    req_file = BASE_DIR / "requirements.txt"
    if req_file.exists():
        cmd = [sys.executable, "-m", "pip", "install", "-r", str(req_file), "--quiet"]
        try:
            subprocess.run(cmd, check=True)
            print("  + Dependencies installed/verified.")
        except Exception as e:
            print(f"  ! Note during pip install: {e}")
    else:
        print("  ! requirements.txt not found, skipping.")

def download_cloudflared():
    print("\n[3/4] Checking Cloudflare Tunnel binary...", flush=True)
    if CLOUDFLARED_EXE.exists() and CLOUDFLARED_EXE.stat().st_size > 10_000_000:
        print(f"  + cloudflared.exe already exists ({CLOUDFLARED_EXE.stat().st_size // (1024*1024)} MB).")
        return

    print(f"  + Downloading cloudflared-windows-amd64.exe from official release...")
    print(f"    Source: {CLOUDFLARED_URL}")
    try:
        req = urllib.request.Request(CLOUDFLARED_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as resp, open(CLOUDFLARED_EXE, 'wb') as out:
            shutil.copyfileobj(resp, out)
        print(f"  + Download complete: {CLOUDFLARED_EXE.stat().st_size // (1024*1024)} MB saved to {CLOUDFLARED_EXE}")
    except Exception as e:
        print(f"  ! Download failed: {e}")
        print("  ! You can manually download cloudflared-windows-amd64.exe and save it to server_host/bin/cloudflared.exe")

def verify_setup():
    print("\n[4/4] Verifying host readiness...", flush=True)
    cf_ok = CLOUDFLARED_EXE.exists() and CLOUDFLARED_EXE.stat().st_size > 10_000_000
    db_file = BASE_DIR / "ca_trader.sqlite3"
    db_ok = db_file.exists()

    print(f"  - Cloudflared executable: {'[OK]' if cf_ok else '[MISSING]'}")
    print(f"  - Database (ca_trader.sqlite3): {'[OK]' if db_ok else '[INITIALIZING ON FIRST RUN]'}")
    print("\n" + "=" * 60)
    print("  LAPTOP HOST SETUP COMPLETE!")
    print("  To launch your laptop server, run:")
    print("    start_laptop_server.bat")
    print("=" * 60)

if __name__ == "__main__":
    print("=" * 60)
    print("   CA TRADER LAPTOP SERVER - HOST PREREQUISITE SETUP")
    print("=" * 60)
    ensure_directories()
    install_dependencies()
    download_cloudflared()
    verify_setup()

