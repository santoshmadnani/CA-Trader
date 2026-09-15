content = open('terminal.html', encoding='utf-8', errors='ignore').read()
p = content.find('function renderFundamentals(')
if p == -1: p = content.find('renderFundamentals =')
print('renderFundamentals found at:', p)
if p != -1:
    print(content[p:p+2000].encode('ascii', errors='replace').decode())

