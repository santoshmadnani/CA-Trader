import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = 159123
print(text[idx-100:idx+2500])

