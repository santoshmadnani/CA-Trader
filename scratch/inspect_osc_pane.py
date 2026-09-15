content = open('terminal.html', encoding='utf-8', errors='ignore').read()
p = content.find('// Draw Oscillators in separate pane')
if p == -1: p = content.find('// Oscillators')
if p == -1: p = content.find('oscH')
print('p:', p)
print(content[p:p+1200].encode('ascii', errors='replace').decode())

