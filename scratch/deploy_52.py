#!/usr/bin/env python3
"""Deploy Release 52 (Sentinel pop-up, Passbook, Notifications, Theta Burn, CRUDEOIL Option Chain calibration, Auto-reco loop) to production."""
import subprocess, zipfile, os, time, pathlib, sys, urllib.request, ssl
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE = pathlib.Path(r'c:\Users\SantoshMadnani\Documents\CA_Trader\7')
ZIP_PATH = pathlib.Path(r'c:\Users\SantoshMadnani\Documents\CA_Trader\46.zip')
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

print('=== Release 52 Production Deployment ===')

# Step 1: Package 46.zip
print(f'\n[1/4] Packaging {ZIP_PATH} ...')
with zipfile.ZipFile(ZIP_PATH, 'w', zipfile.ZIP_DEFLATED) as zf:
    for fname in FILES:
        fpath = BASE / fname
        if fpath.exists():
            zf.write(fpath, fname)
            size = fpath.stat().st_size
            print(f'  + {fname:25s} ({size:,} bytes)')
        else:
            print(f'  ! CRITICAL: Missing file {fname}'); sys.exit(1)

print(f'Package created: {ZIP_PATH} ({os.path.getsize(ZIP_PATH):,} bytes)')

# Step 2: Upload via SCP
print(f'\n[2/4] Uploading to {HOST}:/home/ubuntu/46.zip ...')
scp_cmd = [
    'scp', '-i', KEY,
    '-o', 'StrictHostKeyChecking=no',
    '-o', 'BatchMode=yes',
    str(ZIP_PATH),
    f'{HOST}:/home/ubuntu/46.zip'
]
r = subprocess.run(scp_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
print('STDOUT:', r.stdout)
if r.stderr:
    print('STDERR:', r.stderr)
if r.returncode != 0:
    print('ERROR: SCP upload failed'); sys.exit(1)
print('Upload complete.')

# Step 3: Execute deploy.sh
print(f'\n[3/4] Running deploy script on remote server (deploy.sh 46.zip) ...')
ssh_cmd = [
    'ssh', '-i', KEY,
    '-o', 'StrictHostKeyChecking=no',
    '-o', 'BatchMode=yes',
    HOST,
    'sudo /home/ubuntu/deploy.sh 46.zip'
]
r = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=300, encoding='utf-8', errors='replace')
print('DEPLOY OUTPUT:\n', r.stdout)
if r.stderr:
    print('DEPLOY ERRORS:\n', r.stderr)
if r.returncode != 0:
    print(f'ERROR: deploy.sh exited with code {r.returncode}'); sys.exit(1)

# Step 4: Health Check Verification
print('\n[4/4] Verifying health check on production ...')
time.sleep(5)
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

urls = [
    'http://15.252.81.122/health',
    'https://catrader.site/health',
    'http://15.252.81.122/terminal',
    'https://catrader.site/terminal'
]

for url in urls:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            print(f'  ✓ {url} -> Status {resp.status}')
    except Exception as e:
        print(f'  ! {url} -> Error: {e}')

print('\n=== Release 52 Deployment Complete and Verified! ===')

