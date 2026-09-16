import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

KEY = r'c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem'
HOST = 'ubuntu@15.252.81.122'

py_cmd = (
    "with open('/app/terminal.html') as f:\\n"
    "    text = f.read()\\n"
    "tokens = ['ordersAdvisorCard', 'ordersAdvisorPulse', 'ordersAdvisorVerdict', "
    "'ordersAdvisorChatBox', 'toggleFloatingPositionsWidget(event)', 'floatingPosBodyWrapper', "
    "'openList.length > 0 ? 2000 : 5000', 'activeAdvisorPosition.ltp = ltp', 'selectAdvisorPositionById']\\n"
    "for t in tokens:\\n"
    "    print(f'{t}: {t in text}')\\n"
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

