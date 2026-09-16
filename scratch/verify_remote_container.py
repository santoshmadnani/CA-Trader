import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

KEY = r'c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem'
HOST = 'ubuntu@15.252.81.122'

py_cmd = (
    "with open('/app/terminal.html') as f:\n"
    "    text = f.read()\n"
    "print('ordersAdvisorCard:', 'id=\"ordersAdvisorCard\"' in text)\n"
    "print('ordersAdvisorPulse:', 'id=\"ordersAdvisorPulse\"' in text)\n"
    "print('toggleFloatingPositionsWidget(event):', 'toggleFloatingPositionsWidget(event)' in text)\n"
    "print('adaptive 2s auto-sync:', 'openList.length > 0 ? 2000 : 5000' in text)\n"
    "print('live tick hook:', 'window.activeAdvisorPosition.ltp = ltp' in text)\n"
    "print('selectAdvisorPositionById:', 'selectAdvisorPositionById' in text)\n"
)

ssh_cmd = [
    'ssh', '-i', KEY,
    '-o', 'StrictHostKeyChecking=no',
    HOST,
    f'docker exec ca-trader python3 -c "{py_cmd}"'
]

r = subprocess.run(ssh_cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
print("Remote Container Output:")
print(r.stdout)
if r.stderr:
    print("Stderr:", r.stderr)
