import subprocess

KEY = r'c:\Users\SantoshMadnani\Documents\CA_Trader\ca-trader-key.pem'
HOST = 'ubuntu@15.252.81.122'

py_code = """
import zipfile
z = zipfile.ZipFile('/home/ubuntu/35.zip')
print('Server 35.zip namelist:', z.namelist())
for info in z.infolist():
    print(f'  {info.filename}: {info.file_size} bytes, compressed: {info.compress_size}')
test_script = """
import subprocess
zip_path = "/home/ubuntu/46.zip"
cmd = f'unzip -l {zip_path}'
r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
lines = [l for l in r.stdout.splitlines() if "CA_Trader_Login" in l]
print("Lines with CA_Trader_Login:", lines)
"""

cmd = ['ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', HOST, f"python3 -c \"{py_code}\""]
r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
cmd = ['ssh', '-i', KEY, '-o', 'StrictHostKeyChecking=no', HOST, 'python3', '-c', test_script]
r = subprocess.run(cmd, capture_output=True, text=True)
print(r.stdout)
print(r.stderr)

if r.stderr: print("STDERR:", r.stderr)
