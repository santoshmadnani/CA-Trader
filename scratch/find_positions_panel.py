import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

matches = re.findall(r'<div[^>]*id=["\']panel-([^"\']+)["\']', text)
print("All panels:", matches)

navtabs = re.findall(r'data-tab=["\']([^"\']+)["\']', text)
print("All navtabs:", navtabs)

idx = text.find('id="positionsTable"')
if idx != -1:
    print("\nFound positionsTable at", idx)
    print(text[max(0, idx-500):idx+300])

