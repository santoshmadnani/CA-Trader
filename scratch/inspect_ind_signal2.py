content = open('terminal.html', encoding='utf-8', errors='ignore').read()
p = 271595 + 1500
print(content[p:p+1000].encode('ascii', errors='replace').decode())

