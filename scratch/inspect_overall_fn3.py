content = open('app.py', encoding='utf-8', errors='ignore').read()
p = content.find('def overall_recommendation(')
print(content[p+3500:p+5500])

