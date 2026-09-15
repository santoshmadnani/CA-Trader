import subprocess

ssh_key = r"c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem"
remote_host = "ubuntu@15.252.81.122"

script = """
import requests
s = requests.Session()
r = s.get("http://127.0.0.1:8000/api/instruments/search?q=CRUDEOIL").json()
print("Search results for CRUDEOIL:")
for item in r.get("items", [])[:15]:
    print(" ", item.get("symbol"), "|", item.get("name"), "|", item.get("exchange"), "|", item.get("instrument_type"))
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

