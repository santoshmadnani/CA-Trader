import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

lines = text.splitlines(True)
for i in range(17760, 17830):
    print(f'{i}: {lines[i-1]}', end='')

