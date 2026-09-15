#!/usr/bin/env python3
"""Deploy Release 41 to production."""
import subprocess, zipfile, os, time, pathlib, sys
sys.stdout.reconfigure(encoding='utf-8')

BASE = pathlib.Path(r'c:\Users\SantoshMadnani\Documents\CA_Trader\7')
ZIP_PATH = pathlib.Path(r'c:\Users\SantoshMadnani\Documents\CA_Trader\41.zip')
KEY = r'c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem'
HOST = 'ubuntu@15.252.81.122'
FILES = [
    'app.py',
    'CA_Trader_Login.html',
    'Dockerfile',
    'fitness.html',
    'requirements.txt',
    'terminal.html',
    'terminal_selector.html',
]

print('=== Release 41 Deployment ===')

# Step 1: Create zip
print(f'\n[1/4] Creating {ZIP_PATH} ...')
with zipfile.ZipFile(ZIP_PATH, 'w', zipfile.ZIP_DEFLATED) as zf:
    for fname in FILES:
        fpath = BASE / fname
        if fpath.exists():
            zf.write(fpath, fname)
            size = fpath.stat().st_size
            print(f'  + {fname}  ({size:,} bytes)')
        else:
            print(f'  ! MISSING: {fname}')
print(f'Zip created: {ZIP_PATH}')

# Step 2: Upload zip
print(f'\n[2/4] Uploading to {HOST} ...')
scp_cmd = [
    'scp', '-i', KEY,
    '-o', 'StrictHostKeyChecking=no',
    '-o', 'BatchMode=yes',
    str(ZIP_PATH),
    f'{HOST}:/home/ubuntu/41.zip'
]
r = subprocess.run(scp_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
print('STDOUT:', r.stdout)
print('STDERR:', r.stderr)
if r.returncode != 0:
    print('ERROR: SCP failed'); exit(1)
print('Upload complete.')

# Step 3: Deploy on server
print(f'\n[3/4] Running deploy script on server ...')
ssh_cmd = [
    'ssh', '-i', KEY,
    '-o', 'StrictHostKeyChecking=no',
    '-o', 'BatchMode=yes',
    HOST,
    'sudo /home/ubuntu/deploy.sh 41.zip'
]
r = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=300, encoding='utf-8', errors='replace')
print('STDOUT:', r.stdout[-3000:] if r.stdout and len(r.stdout) > 3000 else r.stdout)
print('STDERR:', r.stderr[-2000:] if r.stderr and len(r.stderr) > 2000 else r.stderr)
if r.returncode != 0:
    print('ERROR: Deployment script returned non-zero code'); exit(1)

# Step 4: Verify health
print(f'\n[4/4] Verifying health ...')
time.sleep(3)
ssh_cmd_status = [
    'ssh', '-i', KEY,
    '-o', 'StrictHostKeyChecking=no',
    '-o', 'BatchMode=yes',
    HOST,
    'sudo docker ps --filter name=ca-trader && curl -sI https://catrader.site/health || curl -sI http://127.0.0.1:8000/health'
]
r2 = subprocess.run(ssh_cmd_status, capture_output=True, text=True, timeout=30, encoding='utf-8', errors='replace')
print('Status check:\n', r2.stdout)

print('\n=== Release 41 Deployment Complete ===')

