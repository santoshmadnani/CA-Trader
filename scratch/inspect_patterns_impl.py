content = open('terminal.html', encoding='utf-8', errors='ignore').read()
p = content.find('async function loadChartPatterns()')
print(content[p:p+1800].encode('ascii', errors='replace').decode())

