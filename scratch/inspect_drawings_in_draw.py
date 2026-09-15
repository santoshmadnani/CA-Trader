content = open('terminal.html', encoding='utf-8', errors='ignore').read()
p = content.find('state.drawings.forEach((q,idx)=>{')
if p == -1: p = content.find('state.drawings.forEach(')
print('state.drawings in draw found at:', p)
if p != -1:
    print(content[p:p+1800].encode('ascii', errors='replace').decode())

