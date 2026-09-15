import subprocess

KEY = r'c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem'
HOST = 'ubuntu@15.252.81.122'
cmd = ['ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', HOST, '''sudo docker exec ca-trader python3 -c "
import sqlite3, hashlib
conn = sqlite3.connect('/app/data/ca_trader.db')
c = conn.cursor()
row = c.execute('SELECT password_hash FROM users WHERE id=1').fetchone()
print('Current hash:', row[0])
# Set password using app.py hashing mechanism
import hashlib, os
# Let's check what hash function app.py uses
import inspect
import app
h = app.hash_password('Trader@123')
c.execute('UPDATE users SET password_hash=? WHERE id=1', (h,))
conn.commit()
print('Updated hash to:', h)
"''']
r = subprocess.run(cmd, capture_output=True, text=True)
print('STDOUT:', r.stdout)
print('STDERR:', r.stderr)

