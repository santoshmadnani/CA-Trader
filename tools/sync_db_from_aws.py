#!/usr/bin/env python3
"""
tools/sync_db_from_aws.py
Synchronizes the production SQLite database from AWS EC2 to your local laptop.
1. Connects to AWS EC2 via SSH using ca-trader-key.pem.
2. Dumps /home/ubuntu/ca-trader-data/ca_trader.sqlite3 safely.
3. Creates a local backup before overwriting app/ca_trader.sqlite3.
4. Verifies database integrity after download.
"""

import sys
import os
import shutil
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
LOCAL_DB = BASE_DIR / "ca_trader.sqlite3"
BACKUP_DIR = BASE_DIR / "server_host" / "backups"
KEY_PATH = BASE_DIR.parent / "ca-trader-key.pem"
HOST = "ubuntu@15.252.81.122"
REMOTE_DB = "/home/ubuntu/ca-trader-data/ca_trader.sqlite3"

def main():
    print("=" * 65)
    print("      CA TRADER - DATABASE SYNC (AWS EC2 -> LOCAL LAPTOP)")
    print("=" * 65)

    if not KEY_PATH.exists():
        print(f"[FAIL] SSH key not found at {KEY_PATH}")
        return 1

    # 1. Backup local DB if it exists
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if LOCAL_DB.exists() and LOCAL_DB.stat().st_size > 0:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        b_dest = BACKUP_DIR / f"pre_sync_{ts}.sqlite3"
        shutil.copy2(LOCAL_DB, b_dest)
        print(f"[1/3] Local backup preserved: {b_dest.name} ({b_dest.stat().st_size // 1024} KB)")
    else:
        print("[1/3] No existing local database, creating fresh sync...")

    # 2. Stream database from EC2
    print(f"\n[2/3] Fetching live database from EC2 ({REMOTE_DB})...")
    ssh_cmd = [
        "ssh", "-n", "-i", str(KEY_PATH),
        "-o", "StrictHostKeyChecking=no",
        "-o", "BatchMode=yes",
        HOST,
        f"cat {REMOTE_DB}"
    ]

    r = subprocess.run(ssh_cmd, capture_output=True, timeout=120)
    if r.returncode != 0 or len(r.stdout) < 1000:
        print(f"[FAIL] Failed to fetch database. Return code: {r.returncode}")
        if r.stderr:
            print(f"Error: {r.stderr.decode('utf-8', errors='replace').strip()}")
        return 1

    with open(LOCAL_DB, "wb") as f:
        f.write(r.stdout)
    print(f"  + Downloaded {len(r.stdout) // 1024} KB into {LOCAL_DB.name}")

    # 3. Verify SQLite integrity
    print("\n[3/3] Verifying downloaded database integrity...")
    try:
        conn = sqlite3.connect(LOCAL_DB)
        c = conn.cursor()
        c.execute("PRAGMA integrity_check;")
        res = c.fetchone()[0]
        if res != "ok":
            print(f"[FAIL] SQLite integrity check failed: {res}")
            return 1

        c.execute("SELECT count(*) FROM users;")
        users_count = c.fetchone()[0]
        c.execute("SELECT count(*) FROM recommendations;")
        reco_count = c.fetchone()[0]
        conn.close()

        print(f"  + PRAGMA integrity_check: {res}")
        print(f"  + Total Users: {users_count}")
        print(f"  + Total Recommendations: {reco_count}")
        print("\n" + "=" * 65)
        print("  DATABASE SYNCHRONIZATION SUCCESSFUL!")
        print("=" * 65)
        return 0
    except Exception as e:
        print(f"[FAIL] Error verifying database: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

