import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('renderPositionsTable')
print(text[idx+3400:idx+5500])

