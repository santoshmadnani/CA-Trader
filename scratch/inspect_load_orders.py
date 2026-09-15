content = open('terminal.html', encoding='utf-8', errors='ignore').read()
p = content.find('async function loadOrders(')
if p == -1: p = content.find('function loadOrders(')
print('loadOrders found at:', p)
if p != -1:
    print(content[p:p+2000].encode('ascii', errors='replace').decode())

