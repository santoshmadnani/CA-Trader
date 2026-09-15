content = open('terminal.html', encoding='utf-8', errors='ignore').read()
p = 194820 + 1900
print(content[p:p+1000].encode('ascii', errors='replace').decode())

