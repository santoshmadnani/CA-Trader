import subprocess

KEY = r'c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem'
HOST = 'ubuntu@15.252.81.122'

bash_cmd = """
ZIP=/home/ubuntu/35.zip
for f in Dockerfile app.py requirements.txt terminal.html CA_Trader_Login.html; do
    if ! unzip -l "$ZIP" | grep -qE "[[:space:]]${f}$"; then
        echo "MISSING: $f"
    else
        echo "FOUND: $f"
    fi
done
"""

cmd = ['ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', HOST, f"bash -c '{bash_cmd}'"]
r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
print(r.stdout)
print(r.stderr)

