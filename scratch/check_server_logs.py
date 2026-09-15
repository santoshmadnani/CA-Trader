import subprocess

cmd = [
    'ssh', '-i', r'c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem',
    '-o', 'StrictHostKeyChecking=no',
    'ubuntu@15.252.81.122',
    "sudo docker logs ca-trader --tail 150"
]
r = subprocess.run(cmd, capture_output=True, text=True)
print("STDOUT:\n", r.stdout)
print("STDERR:\n", r.stderr)

