content = open('terminal.html', encoding='utf-8', errors='ignore').read()
p = 353072
print(content[p-1000:p-450].encode('ascii', errors='replace').decode())

