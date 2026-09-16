import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('data-pos-symbol')
print('data-pos-symbol at:', idx)
print(text[idx-50:idx+400])

