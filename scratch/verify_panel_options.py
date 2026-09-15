import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('terminal.html', encoding='utf-8') as f:
    text = f.read()

pos = text.find('id="panel-options"')
end = text.find('</div>\n    </div>', pos)
print(text[pos:pos+1600])
