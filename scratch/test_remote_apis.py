import subprocess

ssh_key = r"c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem"
remote_host = "ubuntu@15.252.81.122"

python_cmd = (
    "import sqlite3, urllib.request, json\n"
    "c = sqlite3.connect('ca_trader.sqlite3')\n"
    "row = c.execute('SELECT token FROM login_sessions ORDER BY id DESC LIMIT 1').fetchone()\n"
    "token = row[0] if row else None\n"
    "print('Token:', token[:10] if token else 'None')\n"
    "headers = {'Cookie': f'session={token}'} if token else {}\n"
    "def test(u):\n"
    "    try:\n"
    "        req = urllib.request.Request('http://127.0.0.1:8000' + u, headers=headers)\n"
    "        with urllib.request.urlopen(req, timeout=5) as r:\n"
    "            data = r.read()\n"
    "            print(u, r.status, len(data))\n"
    "    except Exception as e:\n"
    "        print(u, 'ERROR:', e)\n"
    "test('/api/news/ca-ai-feed?symbol=NIFTY&mode=all')\n"
    "test('/api/analysis/chart-bundle/NIFTY?timeframe=5m')\n"
    "test('/api/recommendations/history')\n"
    "test('/api/market/movers')\n"
    "test('/api/analysis/fundamental/NIFTY')\n"
)

res = subprocess.run([
    "ssh", "-n", "-i", ssh_key,
    "-o", "StrictHostKeyChecking=no",
    remote_host,
    f"docker exec ca-trader python3 -c \"{python_cmd}\""
], capture_output=True, text=True)

print("STDOUT:\n" + res.stdout)
if res.stderr:
    print("STDERR:\n" + res.stderr)

