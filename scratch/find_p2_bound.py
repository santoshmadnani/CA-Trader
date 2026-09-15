content = open('terminal.html', encoding='utf-8', errors='ignore').read()
p2 = content.find('async function loadOrders(){')
p2_end = content.find('async function loadAutoTrade', p2)
if p2_end == -1: p2_end = content.find('function loadAutoTrade', p2)
print('p2:', p2, 'p2_end:', p2_end)
print(content[p2_end-150:p2_end+50].encode('ascii', errors='replace').decode())

