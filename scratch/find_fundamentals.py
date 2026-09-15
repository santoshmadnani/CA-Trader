import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('terminal.html', encoding='utf-8') as f:
    text = f.read()

pos = text.find('Fundamentals')
while pos != -1:
    print(text[max(0, pos-100):pos+150])
    pos = text.find('Fundamentals', pos+1)
