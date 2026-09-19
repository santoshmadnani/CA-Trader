import subprocess

KEY = r'c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem'
HOST = 'ubuntu@15.252.81.122'

py_code = """
with open('/home/ubuntu/deploy.sh', 'rb') as f:
    data = f.read()
print('Has CRLF:', b'\\r' in data)
lines = data.splitlines()
for i, l in enumerate(lines[35:50], 36):
    print(f'{i}: {repr(l)}')
    lines = f.read().splitlines()
for i in range(40, min(58, len(lines))):
    print(f'{i+1}: {repr(lines[i])}')
"""

cmd = ['ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', HOST, f"python3 -c \"{py_code}\""]
r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
print(r.stdout)
print(r.stderr)

