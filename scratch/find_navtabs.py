import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

for m in re.finditer(r'data-tab=[\'"]([a-z0-9_\-]+)[\'"]', text):
    print(f'at {m.start()}: data-tab="{m.group(1)}"')

