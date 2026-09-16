import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('window.updateFloatingPositionsWidget = async function')
print(text[idx+1500:idx+4000])

