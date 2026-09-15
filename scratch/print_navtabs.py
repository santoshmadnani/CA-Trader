import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('terminal.html', encoding='utf-8') as f:
    text = f.read()

pos = text.find('id="navtabs"')
end = text.find('</div>\n\n<div class="layout">', pos)
print(text[pos:end+10])

