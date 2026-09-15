import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('terminal.html', encoding='utf-8') as f:
    text = f.read()

pos = text.find('id="panel-charts"')
print(text[max(0, pos-800):pos+300])
