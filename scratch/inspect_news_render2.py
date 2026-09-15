content = open('terminal.html', encoding='utf-8', errors='ignore').read()
p = content.find('async function loadNewsByCaAi(')
print(content[p+1500:p+3200].encode('ascii', errors='replace').decode())

