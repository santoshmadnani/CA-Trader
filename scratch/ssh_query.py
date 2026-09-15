import subprocess

KEY = r'c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem'
HOST = 'ubuntu@15.252.81.122'
cmd = ['ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', HOST, 'sudo docker exec ca-trader python3 -c "import sqlite3; conn = sqlite3.connect(\'/app/data/ca_trader.db\'); print(conn.cursor().execute(\'SELECT id, email, role FROM users\').fetchall())"']
r = subprocess.run(cmd, capture_output=True, text=True)
print('STDOUT:', r.stdout)
print('STDERR:', r.stderr)

