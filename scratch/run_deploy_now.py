import subprocess
import time
import urllib.request
import ssl

KEY = r'c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem'
HOST = 'ubuntu@15.252.81.122'

cmd = ['ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', HOST, 'sudo /home/ubuntu/deploy.sh']
r = subprocess.run(cmd, capture_output=True, text=True, timeout=300, encoding='utf-8')
print('STDOUT:\n', r.stdout)
print('STDERR:\n', r.stderr)
print('Exit code:', r.returncode)
print("Executing sudo /home/ubuntu/deploy.sh ...")
cmd = [
    'ssh', '-i', KEY,
    '-o', 'StrictHostKeyChecking=no',
    '-o', 'BatchMode=yes',
    HOST,
    'sudo /home/ubuntu/deploy.sh'
]

r = subprocess.run(cmd, capture_output=True, text=True, timeout=300, encoding='utf-8', errors='replace')
print("STDOUT:")
print(r.stdout[-2500:] if len(r.stdout) > 2500 else r.stdout)
if r.stderr:
    print("STDERR:")
    print(r.stderr[-1000:] if len(r.stderr) > 1000 else r.stderr)

print("Exit code:", r.returncode)

if r.returncode == 0:
    print("\nVerifying health check...")
    time.sleep(5)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    for url in ['https://catrader.site/health', 'https://catrader.site/terminal']:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=12, context=ctx) as resp:
                print(f"  ✓ {url} -> Status {resp.status}")
        except Exception as e:
            print(f"  ! {url} -> Error: {e}")
