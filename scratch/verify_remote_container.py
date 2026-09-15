import subprocess

KEY = r'c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem'
HOST = 'ubuntu@15.252.81.122'

cmd = ['ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', HOST, 'sudo docker exec ca-trader grep -c "panel-dashboard" terminal.html']
r = subprocess.run(cmd, capture_output=True, text=True)
print('Container panel-dashboard occurrences:', r.stdout.strip())

cmd2 = ['ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', HOST, 'sudo docker exec ca-trader grep -c "let lastTickX" terminal.html']
r2 = subprocess.run(cmd2, capture_output=True, text=True)
print('Container let lastTickX occurrences:', r2.stdout.strip())

