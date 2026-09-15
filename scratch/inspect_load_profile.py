content = open('terminal.html', encoding='utf-8', errors='ignore').read()
p = content.find('function loadProfile(')
if p == -1: p = content.find('loadProfile =')
print('loadProfile found at:', p)
if p != -1:
    print(content[p:p+1200].encode('ascii', errors='replace').decode())

