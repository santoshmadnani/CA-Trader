import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx_btn = text.find('id="fpMinBtn"')
line_btn = text[:idx_btn].count('\n') + 1
print('Line at fpMinBtn:', line_btn)

idx_toggle = text.find('window.toggleFloatingPositionsWidget = function')
line_toggle = text[:idx_toggle].count('\n') + 1
print('Line at toggle fn:', line_toggle)

idx_render = text.find('function renderPositionAdvisorData(adv)')
line_render = text[:idx_render].count('\n') + 1
print('Line at renderPositionAdvisorData:', line_render)

lines = text.splitlines(True)
print('\n--- fpMinBtn snippet ---')
for i in range(line_btn - 2, line_btn + 5):
    print(f'{i}: {lines[i-1]}', end='')

print('\n--- toggle fn snippet ---')
for i in range(line_toggle - 2, line_toggle + 14):
    print(f'{i}: {lines[i-1]}', end='')

