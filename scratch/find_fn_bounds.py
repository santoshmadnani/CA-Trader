content = open('terminal.html', encoding='utf-8', errors='ignore').read()
p1 = content.find('function renderFundamentals(d){')
p1_end = content.find('// ---------------- Market movers ----------------', p1)
print('p1:', p1, 'p1_end:', p1_end)
print(content[p1_end-100:p1_end].encode('ascii', errors='replace').decode())

p2 = content.find('async function loadOrders(){')
p2_end = content.find('// ---------------- Auto-trade controls ----------------', p2)
print('p2:', p2, 'p2_end:', p2_end)
print(content[p2_end-100:p2_end].encode('ascii', errors='replace').decode())

