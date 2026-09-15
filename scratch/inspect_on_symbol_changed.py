content = open('terminal.html', encoding='utf-8', errors='ignore').read()
p = content.find('async function onSymbolChanged(')
if p == -1: p = content.find('function onSymbolChanged(')
if p == -1: p = content.find('onSymbolChanged =')
if p == -1: p = content.find('onSymbolChanged=')
print('p:', p)
if p != -1:
    print(content[p:p+1500].encode('ascii', errors='replace').decode())

