content = open('terminal.html', encoding='utf-8', errors='ignore').read()
p = content.find('function loadChart(){')
print(content[p+1000:p+2500].encode('ascii', errors='replace').decode())

