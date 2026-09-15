import subprocess

KEY = r'c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem'
HOST = 'ubuntu@15.252.81.122'

py_code = """
import subprocess
r = subprocess.run(['unzip', '-l', '/home/ubuntu/35.zip'], capture_output=True, text=True)
print('STDOUT:')
print(r.stdout)
for f in ['Dockerfile', 'app.py', 'requirements.txt', 'terminal.html', 'CA_Trader_Login.html']:
    matches = [l for l in r.stdout.splitlines() if f in l]
    print(f'Looking for {f}: {matches}')
"""

cmd = ['ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', HOST, f"python3 -c \"{py_code}\""]
r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
print(r.stdout)
print(r.stderr)

