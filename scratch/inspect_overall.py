content = open('app.py', encoding='utf-8', errors='ignore').read()
p = content.find('/api/analysis/overall/{instrument}')
print(content[p:p+1500])

