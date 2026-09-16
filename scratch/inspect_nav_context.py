import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('data-tab="reports"')
if idx != -1:
    start = max(0, idx - 800)
    end = min(len(text), idx + 800)
    print("SURROUNDING NAV CONTEXT:")
    print(text[start:end])
else:
    print("data-tab='reports' not found")

