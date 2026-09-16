import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('window.executePositionSquareOff')
print('executePositionSquareOff definition at:', idx)
print(text[idx-50:idx+4000])

