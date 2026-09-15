import subprocess

KEY = r'c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem'
HOST = 'ubuntu@15.252.81.122'

cmd = ['ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', HOST, 'sudo /home/ubuntu/deploy.sh']
r = subprocess.run(cmd, capture_output=True, text=True, timeout=300, encoding='utf-8')
print('STDOUT:\n', r.stdout)
print('STDERR:\n', r.stderr)
print('Exit code:', r.returncode)

