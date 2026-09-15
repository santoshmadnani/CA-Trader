import subprocess

KEY = r'c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem'
HOST = 'ubuntu@15.252.81.122'

cmd = ['ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', HOST, 'docker ps']
r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
print('Containers:\n', r.stdout)

