content = open('terminal.html', encoding='utf-8', errors='ignore').read()
p = 258476
print(content[p-200:p+1800].encode('ascii', errors='replace').decode())

