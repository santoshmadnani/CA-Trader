import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('terminal.html', encoding='utf-8') as f:
    text = f.read()

pos = text.find('id="mainNavtabs"')
end = text.find('</div>', pos + 300)
print(text[pos:end+10])
