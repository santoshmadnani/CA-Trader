import subprocess

ssh_key = r"c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem"
remote_host = "ubuntu@15.252.81.122"

script = """
import sqlite3
for path in ['/app/data/ca_trader.sqlite3', '/app/ca_trader.sqlite3']:
    try:
        conn = sqlite3.connect(path)
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        print(path, 'TABLES:', tables)
        for t in tables:
            cols = [r[1] for r in conn.execute(f"PRAGMA table_info({t})").fetchall()]
            print(' ', t, cols)
    except Exception as e:
        print(path, 'ERR:', e)
"""

res = subprocess.run([
    "ssh", "-n", "-i", ssh_key,
    "-o", "StrictHostKeyChecking=no",
    remote_host,
    f"docker exec ca-trader python3 -c {subprocess.list2cmdline([script])}"
], capture_output=True, text=True)

print(res.stdout)
if res.stderr:
    print("STDERR:", res.stderr)

