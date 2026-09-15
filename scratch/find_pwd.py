import subprocess

KEY = r'c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem'
HOST = 'ubuntu@15.252.81.122'

remote_script = """
import os, base64, hashlib, hmac

encoded = '5CltsUQznKhB2JoaOqENEndj38CxCfYyIubVj7PRdIUMidWqhYkb9TCXqWt3gcqI'
raw = base64.urlsafe_b64decode(encoded.encode())
salt, expected = raw[:16], raw[16:]

def test_pwd(pwd):
    actual = hashlib.pbkdf2_hmac("sha256", pwd.encode(), salt, 210_000)
    return hmac.compare_digest(expected, actual)

# check common passwords or env
cand = [
    os.getenv('CA_ADMIN_PASSWORD', ''),
    'Admin@123',
    'admin@123',
    'Santosh@123',
    'SantoshMadnani',
    'Santosh123',
    'Santosh@1234',
    'Trading@123',
    'CATrader@123',
    'ca-trader',
    'password'
]
for c in cand:
    if c and test_pwd(c):
        print('FOUND PASSWORD:', c)
        break
else:
    print('Password not in standard list. CA_ADMIN_PASSWORD is:', repr(os.getenv('CA_ADMIN_PASSWORD')))
"""

cmd = [
    'ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', HOST,
    f'docker exec ca-trader python3 -c "{remote_script}"'
]

r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
print('STDOUT:', r.stdout)
print('STDERR:', r.stderr)

