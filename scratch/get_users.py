import subprocess

KEY = r'c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem'
HOST = 'ubuntu@15.252.81.122'

remote_script = """
import sqlite3
con = sqlite3.connect('/app/data/ca_trader.sqlite3')
cur = con.cursor()
print('Users:', cur.execute('SELECT id, username, email, password_hash FROM users').fetchall())
"""

cmd = [
    'ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', HOST,
    f'docker exec ca-trader python3 -c "{remote_script}"'
]

r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
print('STDOUT:', r.stdout)
print('STDERR:', r.stderr)

