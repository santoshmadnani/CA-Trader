content = open('terminal.html', encoding='utf-8', errors='ignore').read()
p = content.find('// Draw Oscillators in separate pane')
if p == -1: p = content.find('oscH')
print(content[p+1000:p+2500].encode('ascii', errors='replace').decode())

