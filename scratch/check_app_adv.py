import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('/api/positions/advisor')
print('advisor endpoint at:', idx)
print(text[idx-50:idx+2500])

