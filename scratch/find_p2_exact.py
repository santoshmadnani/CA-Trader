content = open('terminal.html', encoding='utf-8', errors='ignore').read()
p2 = content.find('async function loadOrders(){')
p2_end = content.find('bindPortfolioActions()', p2)
print('p2_end:', p2_end)
print(content[p2:p2_end+25].encode('ascii', errors='replace').decode())

