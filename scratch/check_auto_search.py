import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = 344267
print(text[idx-200:idx+1500])

