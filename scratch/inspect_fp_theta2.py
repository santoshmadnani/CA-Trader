import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find("const fpThetaBurnEl = document.getElementById('fpThetaBurn');")
if idx != -1:
    print(text[idx+500:idx+1200])

