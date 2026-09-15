content = open('terminal.html', encoding='utf-8', errors='ignore').read()
p1 = content.find('function renderFundamentals(')
print('--- renderFundamentals ---')
print(content[p1:p1+400].encode('ascii', errors='replace').decode())

p2 = content.find('async function loadPortfolioSnapshot(')
print('--- loadPortfolioSnapshot ---')
print(content[p2:p2+400].encode('ascii', errors='replace').decode())

