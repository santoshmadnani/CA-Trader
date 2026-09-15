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

t0 = time.time()
r = s.get("http://127.0.0.1:8000/api/analysis/overall/NIFTY?timeframe=5m")
t1 = time.time()
print(f"Status: {r.status_code} in {t1-t0:.2f}s")
if r.status_code == 200:
    d = r.json()
    print("Keys:", list(d.keys()))
    print("Recommendation:", d.get("recommendation"))
    print("Signal:", d.get("signal"))
    print("Action:", d.get("action"))
    print("Entry:", d.get("entry"))
    print("Target:", d.get("target"))
    print("Stop loss:", d.get("stop_loss"))
    print("Display symbol:", d.get("display_symbol"))
    print("Instrument:", d.get("instrument"))
else:
    print("Error:", r.text[:300])
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

