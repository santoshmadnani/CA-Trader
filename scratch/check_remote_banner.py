import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

KEY = r'c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem'
HOST = 'ubuntu@15.252.81.122'

py_cmd = (
    "with open('/app/terminal.html') as f:\n"
    "    text = f.read()\n"
    "idx = text.find('ordersAdvisorCard')\n"
    "print('idx of ordersAdvisorCard in container:', idx)\n"
    "idx2 = text.find('positionAdvisoryBanner')\n"
    "print('idx of positionAdvisoryBanner in container:', idx2)\n"
    "print(text[idx2:idx2+500])\n"
)

ssh_cmd = [
    'ssh', '-i', KEY,
    '-o', 'StrictHostKeyChecking=no',
    HOST,
    f'docker exec ca-trader python3 -c "{py_cmd}"'
]

r = subprocess.run(ssh_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
print("Remote Output:")
print(r.stdout)

