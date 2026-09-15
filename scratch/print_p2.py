content = open('terminal.html', encoding='utf-8', errors='ignore').read()
p2 = content.find('async function loadOrders(){')
print(content[p2:p2+1500].encode('ascii', errors='replace').decode())

