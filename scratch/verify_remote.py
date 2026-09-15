import subprocess
import json

ssh_key = r"c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem"
remote_host = "ubuntu@15.252.81.122"

cmd = [
    "ssh", "-n", "-i", ssh_key,
    "-o", "StrictHostKeyChecking=no",
    "-o", "BatchMode=yes",
    remote_host,
    "sudo docker ps --format '{{.Names}} | {{.Image}} | {{.Status}}'; sudo docker logs --tail 25 ca-trader"
]

res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
print("--- DOCKER STATUS & LOGS ---")
print(res.stdout)
if res.stderr:
    print("STDERR:", res.stderr)
