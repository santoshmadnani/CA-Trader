content = open('terminal.html', encoding='utf-8', errors='ignore').read()
p = 353072
print(content[p-500:p+500].encode('ascii', errors='replace').decode())

