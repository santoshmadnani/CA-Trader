with open('terminal.html', encoding='utf-8') as f:
    text = f.read()

# Right before <div class="panel" id="panel-charts">, add the two closing divs
pos = text.find('<div class="panel" id="panel-charts">')
text = text[:pos] + '    </div>\n    </div>\n\n    ' + text[pos:]

with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("Added two closing divs before panel-charts.")

