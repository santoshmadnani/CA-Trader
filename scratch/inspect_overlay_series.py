content = open('terminal.html', encoding='utf-8', errors='ignore').read()
p = content.find('function appliedOverlaySeries(')
print('appliedOverlaySeries found at:', p)
if p != -1:
    print(content[p:p+2500].encode('ascii', errors='replace').decode())

