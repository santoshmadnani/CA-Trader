import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('id="caEditBar"')
if idx != -1:
    print(text[idx-50:idx+600])

