import subprocess

ssh_key = r"c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem"
remote_host = "ubuntu@15.252.81.122"

script = """
from app import UPSTOX

s = UPSTOX.search_instruments("CRUDEOIL 17 SEP", exchanges="MCX", segments="ALL")
rows = s.get("data", [])
print(f"Search 'CRUDEOIL 17 SEP' count: {len(rows)}")
for r in rows[:10]:
    print(" ", r.get("trading_symbol"), "|", r.get("instrument_key"), "|", r.get("strike_price"), "|", r.get("instrument_type"))
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

