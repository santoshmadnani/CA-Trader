import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('id="fpThetaBurn"')
if idx != -1:
    print("fpThetaBurn:", repr(text[idx:idx+120]))

idx = text.find('id="ordersThetaBurn"')
if idx != -1:
    print("ordersThetaBurn:", repr(text[idx:idx+120]))

