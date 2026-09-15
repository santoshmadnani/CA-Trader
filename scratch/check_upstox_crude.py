import subprocess

ssh_key = r"c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem"
remote_host = "ubuntu@15.252.81.122"

script = """
import json
from app import UPSTOX

# Test 1: Upstox option contracts for CRUDEOIL
try:
    contracts = UPSTOX.option_contracts("CRUDEOIL")
    data = contracts.get("data", [])
    print(f"UPSTOX.option_contracts('CRUDEOIL') count: {len(data)}")
    if data:
        print("Sample contract:", data[0])
except Exception as e:
    print("UPSTOX.option_contracts('CRUDEOIL') error:", e)

# Test 2: Upstox option chain for CRUDEOIL
try:
    chain = UPSTOX.option_chain("CRUDEOIL")
    print("UPSTOX.option_chain('CRUDEOIL') keys:", list(chain.keys()) if chain else None)
    if chain and chain.get("strikes"):
        print(f"Strikes count: {len(chain['strikes'])}")
        print("Sample strike:", chain['strikes'][0])
except Exception as e:
    print("UPSTOX.option_chain('CRUDEOIL') error:", e)

# Test 3: Search for options with 17 SEP or 10000 CE
try:
    s = UPSTOX.search_instruments("CRUDEOIL 10000", exchanges="MCX,NSE", segments="ALL")
    rows = s.get("data", [])
    print(f"Search 'CRUDEOIL 10000' count: {len(rows)}")
    for r in rows[:5]:
        print(" ", r.get("trading_symbol"), "|", r.get("instrument_key"), "|", r.get("expiry"))
except Exception as e:
    print("Search error:", e)
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

