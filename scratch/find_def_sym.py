content = open('terminal.html', encoding='utf-8', errors='ignore').read()
p = content.find('function selectedSymbol')
print(content[p:p+300])

