import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('terminal.html', encoding='utf-8') as f:
    text = f.read()

pos = text.find('id="panel-options"')
# find opening divs before this
before = text[:pos]
lines = before.splitlines()
print("\n".join(lines[-25:]))
