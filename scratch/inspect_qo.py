import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

m = re.search(r'id=[\'"]quickOrderModal[\'"]', text)
if m:
    idx = m.start()
    print('quickOrderModal at:', idx)
    print(text[idx-50:idx+2500])

