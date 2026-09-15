import subprocess

cmd = [
    'ssh', '-i', r'c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem',
    '-o', 'StrictHostKeyChecking=no',
    'ubuntu@15.252.81.122',
    "sudo docker exec ca-trader python -c \"import sqlite3; conn=sqlite3.connect('/app/data/ca_trader.sqlite3'); conn.row_factory=sqlite3.Row; groups=[dict(r) for r in conn.execute('SELECT * FROM watchlist_groups WHERE user_id=2').fetchall()]; [g.update({'items': [dict(m) for m in conn.execute('SELECT * FROM watchlist_members WHERE watchlist_id=?', [g['id']]).fetchall()]}) for g in groups]; print(groups)\""
]
r = subprocess.run(cmd, capture_output=True, text=True)
print("STDOUT:\n", r.stdout)

