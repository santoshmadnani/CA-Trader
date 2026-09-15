import subprocess

ssh_key = r"c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem"
remote_host = "ubuntu@15.252.81.122"

script = """
import json
from app import UPSTOX

chain = UPSTOX.option_chain("CRUDEOIL")
print("CRUDEOIL option chain expiry:", chain.get("expiry"))
print("CRUDEOIL option chain spot:", chain.get("spot"))
print("CRUDEOIL option chain strikes count:", len(chain.get("strikes", [])))
if chain.get("strikes"):
    print("Sample strike:", json.dumps(chain["strikes"][0], indent=2))
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

