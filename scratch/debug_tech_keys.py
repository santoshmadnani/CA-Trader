import subprocess

ssh_key = r"c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem"
remote_host = "ubuntu@15.252.81.122"

script = """
import json, base64, time, requests
from itsdangerous import TimestampSigner
from app import AUTH_SECRET

session_dict = {"user_id": 1, "last_seen": time.time()}
session_json = json.dumps(session_dict).encode("utf-8")
signer = TimestampSigner(AUTH_SECRET)
signed_cookie = signer.sign(base64.b64encode(session_json)).decode("utf-8")

s = requests.Session()
s.cookies.set("session", signed_cookie)

r_chart = s.get("http://127.0.0.1:8000/api/analysis/chart-bundle/NSE_INDEX%7CNifty%2050?timeframe=5m").json()
tech = r_chart.get("technical", {})
print("TECH KEYS:", list(tech.keys()))
for k in list(tech.keys()):
    v = tech[k]
    if isinstance(v, (int, float, str, bool)) or v is None:
        print(f"  {k}: {v}")
    elif isinstance(v, list):
        print(f"  {k}: list of length {len(v)}")
    elif isinstance(v, dict):
        print(f"  {k}: dict with keys {list(v.keys())}")
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

