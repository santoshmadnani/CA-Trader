import re

with open('terminal.html', encoding='utf-8', errors='ignore') as f:
    text = f.read()

p = text.find('Add Instrument...')
print('Add Instrument... found at', p)
if p != -1:
    print(text[p-200:p+800].encode('ascii', errors='replace').decode())

