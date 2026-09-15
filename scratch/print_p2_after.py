content = open('terminal.html', encoding='utf-8', errors='ignore').read()
p2 = content.find('async function loadOrders(){')
print(content[p2+1200:p2+2500].encode('ascii', errors='replace').decode())

