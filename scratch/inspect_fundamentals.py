content = open('terminal.html', encoding='utf-8', errors='ignore').read()
p = content.find('async function loadFundamentals(')
if p == -1: p = content.find('function loadFundamentals(')
print('loadFundamentals found at:', p)
if p != -1:
    print(content[p:p+2000].encode('ascii', errors='replace').decode())

