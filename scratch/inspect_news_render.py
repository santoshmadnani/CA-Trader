content = open('terminal.html', encoding='utf-8', errors='ignore').read()
p = content.find('async function loadNewsByCaAi(')
print(content[p:p+2500].encode('ascii', errors='replace').decode())

