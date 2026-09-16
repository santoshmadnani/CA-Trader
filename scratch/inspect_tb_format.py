import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find("const tb = Number(adv.theta_decay_hourly || 0);")
if idx != -1:
    print(text[idx-50:idx+400])

