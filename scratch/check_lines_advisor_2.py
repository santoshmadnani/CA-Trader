import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

lines = text.splitlines(True)
for i in range(17680, 17760):
    print(f'{i}: {lines[i-1]}', end='')

