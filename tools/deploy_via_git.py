#!/usr/bin/env python3
"""
tools/deploy_via_git.py
Automated Zero-Transfer Deployment Script for CA Trader.
Pulls latest changes directly from GitHub on the remote EC2 server,
packages 46.zip on the server, executes deploy.sh, and verifies live health.
Zero file transfers from local laptop -> 100% compliant with Sophos security mandate.
"""

import subprocess
import sys
import time
import urllib.request
import ssl
from pathlib import Path

KEY = r"C:\Users\SantoshMadnani\OneDrive - BDO INDIA SERVICES PRIVATE LIMITED\Personal files\CA_Trader\ca-trader-key.pem"
HOST = "ubuntu@15.252.81.122"

def run_ssh(cmd, timeout=400):
    ssh_cmd = [
        "ssh", "-n", "-i", KEY,
        "-o", "StrictHostKeyChecking=no",
        "-o", "BatchMode=yes",
        HOST,
        cmd
    ]
    r = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
    enc = sys.stdout.encoding or 'utf-8'
    if r.stdout:
        safe_out = r.stdout.encode(enc, errors='replace').decode(enc).strip()
        print(safe_out, flush=True)
    if r.stderr:
        safe_err = r.stderr.encode(enc, errors='replace').decode(enc).strip()
        print(f"[STDERR] {safe_err}", flush=True)
    return r

def main():
    print("=" * 65)
    print("      CA TRADER REMOTE DEPLOYMENT (ZERO LAPTOP TRANSFERS)")
    print("=" * 65)

    # 1. Update repo on EC2 from GitHub
    print("\n[1/4] Syncing GitHub branch CA-Trader-Bifurcated on EC2...")
    r1 = run_ssh("""
    if [ ! -d '/home/ubuntu/ca-trader-repo' ]; then
        git clone -b CA-Trader-Bifurcated https://github.com/santoshmadnani/CA-Trader.git /home/ubuntu/ca-trader-repo
    else
        cd /home/ubuntu/ca-trader-repo && git fetch origin && git checkout CA-Trader-Bifurcated && git reset --hard origin/CA-Trader-Bifurcated
    fi
    cd /home/ubuntu/ca-trader-repo && git log -1 --oneline
    """)
    if r1.returncode != 0:
        print("[FAIL] Git sync failed on EC2.")
        return 1

    # 2. Package 46.zip on EC2
    print("\n[2/4] Packaging 46.zip directly on EC2...")
    pack_cmd = """python3 -c "
import zipfile, os, pathlib
base = pathlib.Path('/home/ubuntu/ca-trader-repo')
out = '/home/ubuntu/46.zip'
if os.path.exists(out): os.remove(out)
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(base):
        if '.git' in root or '__pycache__' in root: continue
        for f in files:
            full = pathlib.Path(root) / f
            rel = full.relative_to(base)
            zf.write(full, str(rel))
print('Pack complete: 46.zip is', os.path.getsize(out), 'bytes')
" """
    r2 = run_ssh(pack_cmd)
    # 2. Package clean 46.zip on EC2
    print("\n[2/4] Packaging clean 46.zip directly on EC2...")
    r2 = run_ssh("python3 /home/ubuntu/pack_clean.py")
    if r2.returncode != 0:
        print("[FAIL] Packaging failed on EC2.")
        return 1

    # 3. Run deploy.sh on EC2
    print("\n[3/4] Executing safe deploy script on EC2 (sudo /home/ubuntu/deploy.sh)...")
    r3 = run_ssh("sudo /home/ubuntu/deploy.sh /home/ubuntu/46.zip", timeout=600)
    if r3.returncode != 0:
        print("[FAIL] deploy.sh returned non-zero exit code.")
        return 1

    # 4. Verify Live Production Health
    print("\n[4/4] Verifying production health endpoints (https://catrader.site)...")
    time.sleep(5)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    urls = [
        "https://catrader.site/health",
        "https://catrader.site/login",
        "https://catrader.site/terminal",
        "http://15.252.81.122/health"
    ]

    all_pass = True
    for u in urls:
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 CA-Trader-Deploy-Check"})
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                print(f"  [PASS] {u} -> Status {resp.status}", flush=True)
        except Exception as e:
            print(f"  [FAIL] {u} -> Error: {e}", flush=True)
            all_pass = False

    print("\n" + "=" * 65)
    if all_pass:
        print(" PRODUCTION DEPLOYMENT & VERIFICATION COMPLETED SUCCESSFULLY!")
        print("=" * 65 + "\n")
        return 0
    else:
        print(" DEPLOYMENT FINISHED WITH WARNINGS ON LIVE ENDPOINTS")
        print("=" * 65 + "\n")
        return 1

if __name__ == '__main__':
    sys.exit(main())
