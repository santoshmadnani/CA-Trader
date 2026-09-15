content = open('app.py', encoding='utf-8', errors='ignore').read()
p = content.find('def overall_recommendation(')
print(content[p+5500:p+7500])

