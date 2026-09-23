#!/usr/bin/env python3
"""
server_host/start_laptop_server.py
One-Click Master Launcher for CA Trader on a Laptop.
1. Reads host_config.json
2. Backs up SQLite database automatically before launch
3. Activates Windows Sleep-Inhibition to keep the server awake while plugged in
4. Launches CA Trader (SelectorEventLoop) on localhost:8000
5. Launches Cloudflare Tunnel to provide an instant, secure public HTTPS URL
"""

import sys
import os
import time
import json
import shutil
import asyncio
import ctypes
import subprocess
import threading
import re
from pathlib import Path
from datetime import datetime

# Windows Sleep Inhibition Constants
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_AWAYMODE_REQUIRED = 0x00000040

def set_sleep_inhibition(enable=True):
    if sys.platform == "win32":
        try:
            if enable:
                ctypes.windll.kernel32.SetThreadExecutionState(
                    ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED
                )
                print("[HOST] Windows Sleep-Inhibition ACTIVATED (Server will not sleep while running).", flush=True)
            else:
                ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
                print("[HOST] Windows Sleep-Inhibition RELEASED.", flush=True)
        except Exception as e:
            print(f"[HOST] Note: Sleep-Inhibition warning: {e}", flush=True)

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
HOST_DIR = BASE_DIR / "server_host"
CONFIG_FILE = HOST_DIR / "host_config.json"
BIN_DIR = HOST_DIR / "bin"
CLOUDFLARED_EXE = BIN_DIR / "cloudflared.exe"

def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "server": {"host": "127.0.0.1", "port": 8000},
        "database": {"canonical_file": "ca_trader.sqlite3", "backup_dir": "server_host/backups", "auto_backup_on_start": True, "max_backups_to_retain": 15},
        "tunnel": {"enabled": True, "mode": "quick", "binary_path": "server_host/bin/cloudflared.exe"}
    }

def backup_database(cfg):
    db_name = cfg.get("database", {}).get("canonical_file", "ca_trader.sqlite3")
    db_path = BASE_DIR / db_name
    backup_dir = BASE_DIR / cfg.get("database", {}).get("backup_dir", "server_host/backups")
    backup_dir.mkdir(parents=True, exist_ok=True)

    if db_path.exists() and db_path.stat().st_size > 0:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = backup_dir / f"ca_trader_{ts}.sqlite3"
        shutil.copy2(db_path, dest)
        print(f"[DB] Automated backup created: {dest.name} ({dest.stat().st_size // 1024} KB)", flush=True)

        # Prune old backups
        max_keep = cfg.get("database", {}).get("max_backups_to_retain", 15)
        backups = sorted(backup_dir.glob("ca_trader_*.sqlite3"), key=os.path.getmtime)
        if len(backups) > max_keep:
            for old in backups[:-max_keep]:
                try:
                    old.unlink()
                except Exception:
                    pass

def run_tunnel_thread(cfg, port):
    if not cfg.get("tunnel", {}).get("enabled", True):
        return None

    if not CLOUDFLARED_EXE.exists():
        print(f"[TUNNEL] cloudflared.exe not found at {CLOUDFLARED_EXE}. Run install_host_prerequisites.bat first to enable tunnel.", flush=True)
        return None

    mode = cfg.get("tunnel", {}).get("mode", "quick")
    if mode == "quick":
        cmd = [str(CLOUDFLARED_EXE), "tunnel", "--url", f"http://127.0.0.1:{port}", "--no-autoupdate"]
    else:
        named = cfg.get("tunnel", {}).get("named_tunnel", {})
        tname = named.get("tunnel_name", "ca-trader-laptop")
        cmd = [str(CLOUDFLARED_EXE), "tunnel", "run", tname]

    print(f"\n[TUNNEL] Launching Cloudflare Tunnel ({mode} mode)...", flush=True)
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    def monitor_tunnel():
        url_found = False
        for line in proc.stdout:
            # Look for assigned quick tunnel URL
            match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
            if match and not url_found:
                url_found = True
                pub_url = match.group(0)
                print("\n" + "=" * 65, flush=True)
                print("  PUBLIC HTTPS TUNNEL ACTIVE FOR YOUR LAPTOP!", flush=True)
                print(f"  Live URL: {pub_url}", flush=True)
                print(f"  Terminal: {pub_url}/terminal", flush=True)
                print("  Access this URL from your phone, tablet, or external browser!", flush=True)
                print("=" * 65 + "\n", flush=True)

    t = threading.Thread(target=monitor_tunnel, daemon=True)
    t.start()
    return proc

def free_port_if_occupied(port):
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(('127.0.0.1', port)) != 0:
            return  # Port is free
    print(f"[PORT] Port {port} is occupied by another process. Terminating previous instance...", flush=True)
    if sys.platform == "win32":
        try:
            out = subprocess.check_output(f"netstat -ano | findstr :{port}", shell=True, text=True)
            for line in out.strip().splitlines():
                if "LISTENING" in line:
                    parts = line.strip().split()
                    pid = parts[-1]
                    if pid and pid != str(os.getpid()):
                        subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
                        print(f"[PORT] Freed port {port} (killed PID {pid}).", flush=True)
                        time.sleep(1.5)
                        break
        except Exception as e:
            print(f"[PORT] Note: {e}", flush=True)

def main():
    print("=" * 65)
    print("        CA TRADER - PORTABLE LAPTOP SERVER LAUNCHER")
    print("=" * 65)

    cfg = load_config()
    server_cfg = cfg.get("server", {})
    host = server_cfg.get("host", "127.0.0.1")
    port = server_cfg.get("port", 8000)

    # 0. Free port if previously occupied
    free_port_if_occupied(port)

    # 1. Database backup
    if cfg.get("database", {}).get("auto_backup_on_start", True):
        backup_database(cfg)

    # 2. Inhibit Windows sleep
    if cfg.get("power_management", {}).get("prevent_system_sleep_while_running", True):
        set_sleep_inhibition(True)

    # 3. Apply SelectorEventLoop on Windows
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except Exception:
            pass

    import uvicorn
    import uvicorn.loops.asyncio
    if sys.platform == "win32":
        uvicorn.loops.asyncio.asyncio_loop_factory = lambda use_subprocess=False: asyncio.SelectorEventLoop

    # 4. Start Cloudflare Tunnel in background
    tunnel_proc = run_tunnel_thread(cfg, port)

    print(f"\n[SERVER] Starting CA Trader backend on http://{host}:{port}...", flush=True)
    try:
        # Change working directory to app root so relative paths work seamlessly
        os.chdir(str(BASE_DIR))
        uvicorn.run("app:app", host=host, port=port, log_level=server_cfg.get("log_level", "info"))
    except KeyboardInterrupt:
        print("\n[SERVER] Shutdown signal received (Ctrl+C).", flush=True)
    finally:
        if tunnel_proc:
            print("[TUNNEL] Terminating Cloudflare Tunnel...", flush=True)
            tunnel_proc.terminate()
        set_sleep_inhibition(False)
        print("[SERVER] Clean shutdown complete.", flush=True)

if __name__ == "__main__":
    main()
