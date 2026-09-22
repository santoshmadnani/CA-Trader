import re

with open('terminal.html', encoding='utf-8', errors='ignore') as f:
with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

p = text.find('Add Instrument...')
print('Add Instrument... found at', p)
if p != -1:
    print(text[p-200:p+800].encode('ascii', errors='replace').decode())
style_end = text.find('</style>')
style_content = text[:style_end]

for i, line in enumerate(style_content.split('\n')):
    if '.sidebar' in line:
        print(f"Line {i+1}: {line[:120]}")
