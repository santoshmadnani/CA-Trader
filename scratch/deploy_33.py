import zipfile
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')

src_dir = r"c:\Users\SantoshMadnani\Documents\CA_Trader\7"
zip_path = r"c:\Users\SantoshMadnani\Documents\CA_Trader\33.zip"
ssh_key = r"c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem"
remote_host = "ubuntu@15.252.81.122"

files_to_pack = [
    "app.py",
    "CA_Trader_Login.html",
    "Dockerfile",
    "fitness.html",
    "requirements.txt",
    "terminal.html",
    "terminal_selector.html"
]

print("1. Creating 33.zip for Release 33...")
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for fname in files_to_pack:
        fpath = os.path.join(src_dir, fname)
        if os.path.exists(fpath):
            z.write(fpath, arcname=fname)
            print(f"  Added {fname} ({os.path.getsize(fpath)} bytes)")
        else:
            print(f"  ERROR: {fname} not found!")
            sys.exit(1)

print(f"33.zip created! Size: {os.path.getsize(zip_path)} bytes")

print("\n2. Uploading 33.zip to server (15.252.81.122)...")
res = subprocess.run([
    "scp", "-i", ssh_key,
    "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=yes",
    zip_path, f"{remote_host}:/home/ubuntu/33.zip"
], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
if res.returncode != 0:
    print("SCP failed:", res.stderr)
    sys.exit(1)
print("Upload complete!")

print("\n3. Running deploy.sh 33.zip on server...")
dp = subprocess.run([
    "ssh", "-n", "-i", ssh_key,
    "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=yes",
    remote_host,
    "sudo /home/ubuntu/deploy.sh 33.zip"
], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=600)

out = dp.stdout or ''
if len(out) > 3000:
    print("...(truncated stdout)...")
    print(out[-3000:])
else:
    print(out)

if dp.returncode != 0:
    print("\nDeploy failed with error code:", dp.returncode)
    print(dp.stderr)
    sys.exit(1)

print("\n4. Deploy script completed successfully!")

