import subprocess
import json
import subprocess, json

ssh_key = r"c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem"
remote_host = "ubuntu@15.252.81.122"
KEY = r'c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem'
HOST = 'ubuntu@15.252.81.122'

cmd = [
    "ssh", "-n", "-i", ssh_key,
    "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=yes",
    remote_host,
    "sudo docker ps --format '{{.Names}} | {{.Image}} | {{.Status}}'; sudo docker logs --tail 25 ca-trader"
]
def run_ssh(remote_cmd):
    cmd = ['ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', HOST, remote_cmd]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout.strip(), r.stderr.strip()

res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
print("--- DOCKER STATUS & LOGS ---")
print(res.stdout)
if res.stderr:
    print("STDERR:", res.stderr)
print("--- Checking container status ---")
out, err = run_ssh("sudo docker ps --filter name=ca-trader --format '{{.Names}} | {{.Image}} | {{.Status}}'")
print("Container:", out)

print("\n--- Checking terminal.html contents inside container ---")
out, _ = run_ssh("sudo docker exec ca-trader grep -c 'floatingPositionWidget' terminal.html")
print("floatingPositionWidget matches:", out)
out, _ = run_ssh("sudo docker exec ca-trader grep -c 'dashConfluenceContainer' terminal.html")
print("dashConfluenceContainer matches:", out)
out, _ = run_ssh("sudo docker exec ca-trader grep -c 'btnLockDrawings' terminal.html")
print("btnLockDrawings matches:", out)
out, _ = run_ssh("sudo docker exec ca-trader grep -c 'toggleNotesSidebar' terminal.html")
print("toggleNotesSidebar matches:", out)

print("\n--- Testing API endpoints via local curl inside server ---")
# Test save recommendation endpoint
save_cmd = """sudo docker exec ca-trader python3 -c "
import urllib.request, json
url = 'http://127.0.0.1:8000/api/recommendations/save'
data = json.dumps({'symbol': 'CRUDEOIL', 'action': 'BUY_CALL', 'entry': 100, 'target': 120, 'stop_loss': 90}).encode()
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')
try:
    with urllib.request.urlopen(req) as resp:
        print('SAVE API SUCCESS:', resp.read().decode())
except Exception as e:
    print('SAVE API ERROR:', e)
" """
out, _ = run_ssh(save_cmd)
print(out)

# Test Crude news
news_cmd = """sudo docker exec ca-trader python3 -c "
import urllib.request, json
url = 'http://127.0.0.1:8000/api/news/ca-ai-feed?symbol=CRUDEOIL'
with urllib.request.urlopen(url) as resp:
    d = json.loads(resp.read().decode())
    print('CRUDE NEWS COUNT:', len(d.get('items', [])))
    if d.get('items'):
        print('FIRST HEADLINE:', d['items'][0].get('title'))
" """
out, _ = run_ssh(news_cmd)
print(out)
