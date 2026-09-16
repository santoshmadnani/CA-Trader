import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('theta_hourly_rupees =')
if idx != -1:
    print(text[idx-200:idx+400])
else:
    print("theta_hourly_rupees = not found")

