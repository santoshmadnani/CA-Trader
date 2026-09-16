import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

lines_before = text[:216491].count('\n') + 1
print('Line number at end_banner:', lines_before)

lines = text.splitlines(True)
for i in range(lines_before - 5, lines_before + 8):
    print(f'{i}: {lines[i-1]}', end='')

