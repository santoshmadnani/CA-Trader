content = open('app.py', encoding='utf-8', errors='ignore').read()
p = content.find('/api/news/discuss')
print(content[p:p+1200])

