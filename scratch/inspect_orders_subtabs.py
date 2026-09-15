content = open('terminal.html', encoding='utf-8', errors='ignore').read()
p = content.find('id="panel-orders"')
print(content[p+1000:p+2000].encode('ascii', errors='replace').decode())

