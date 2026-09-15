import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('id="panel-backtest"')
print(text[idx+6000:idx+10000])

