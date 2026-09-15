content = open('terminal.html', encoding='utf-8', errors='ignore').read()
p = 258476
print(content[p+1500:p+3000].encode('ascii', errors='replace').decode())

