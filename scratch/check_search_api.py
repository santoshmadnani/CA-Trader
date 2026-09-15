import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find instrument_search endpoint
idx = content.find('/api/instruments/search')
ln = content[:idx].count('\n') + 1
print(f'instrument_search route at line {ln}')

lines = content.split('\n')
for i, l in enumerate(lines[max(0,ln-2):ln+60], max(0,ln-2)+1):
    print(f'{i}: {l[:250]}')
