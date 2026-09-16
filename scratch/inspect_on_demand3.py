import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('"/api/recommendations/on-demand"')
if idx == -1:
    idx = text.find("'/api/recommendations/on-demand'")
if idx != -1:
    print(text[idx-50:idx+1200])

