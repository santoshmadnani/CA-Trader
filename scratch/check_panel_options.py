with open('terminal.html', encoding='utf-8') as f:
    text = f.read()

import re
pos = text.find('id="panel-options"')
if pos != -1:
    print(text[pos-50:pos+1500])
else:
    print("panel-options not found")

