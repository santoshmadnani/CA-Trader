import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Check initial markup
print("fpThetaBurn markup:")
idx = text.find('id="fpThetaBurn"')
if idx != -1:
    print(repr(text[idx-40:idx+80]))

print("\nordersThetaBurn markup:")
idx = text.find('id="ordersThetaBurn"')
if idx != -1:
    print(repr(text[idx-40:idx+80]))

