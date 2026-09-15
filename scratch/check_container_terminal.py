import subprocess

cmd = [
    'ssh', '-i', r'c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem',
    '-o', 'StrictHostKeyChecking=no',
    'ubuntu@15.252.81.122',
    "sudo docker exec ca-trader python -c \"with open('/app/terminal.html') as f: t = f.read(); print('terminal.html length in container:', len(t), 'has msThesisBox:', 'msThesisBox' in t, 'has panel-charts:', 'panel-charts' in t)\""
]
r = subprocess.run(cmd, capture_output=True, text=True)
print("STDOUT:", r.stdout)

