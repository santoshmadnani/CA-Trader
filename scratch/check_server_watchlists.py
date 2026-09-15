import subprocess

cmd = [
    'ssh', '-i', r'c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem',
    '-o', 'StrictHostKeyChecking=no',
    'ubuntu@15.252.81.122',
    "sudo docker exec ca-trader python -c \"import sqlite3; conn=sqlite3.connect('/app/data/ca_trader.sqlite3'); print('groups:', conn.execute('SELECT * FROM watchlist_groups').fetchall()); print('users:', conn.execute('SELECT id, email, role FROM users').fetchall()); print('members:', conn.execute('SELECT * FROM watchlist_members').fetchall())\""
]
r = subprocess.run(cmd, capture_output=True, text=True)
print("STDOUT:\n", r.stdout)
print("STDERR:\n", r.stderr)

