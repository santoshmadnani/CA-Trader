import subprocess

KEY = r'c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem'
HOST = 'ubuntu@15.252.81.122'

script = """
from app import db_exec
rows = db_exec("SELECT * FROM positions", fetch="all")
print("COUNT:", len(rows))
for r in rows:
    print(dict(r))

orders = db_exec("SELECT * FROM orders ORDER BY created_at DESC LIMIT 10", fetch="all")
print("RECENT ORDERS COUNT:", len(orders))
for o in orders:
    print(dict(o))
"""

cmd = ['ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', HOST,
       f'sudo docker exec ca-trader python3 -c "{script}"']
r = subprocess.run(cmd, capture_output=True, text=True)
print("STDOUT:\n", r.stdout)
if r.stderr:
    print("STDERR:\n", r.stderr)

