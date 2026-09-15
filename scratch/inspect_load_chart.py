content = open('terminal.html', encoding='utf-8', errors='ignore').read()
p = content.find('function loadChart(')
if p == -1: p = content.find('async function loadChart(')
print('p:', p)
if p != -1:
    print(content[p:p+1200].encode('ascii', errors='replace').decode())

