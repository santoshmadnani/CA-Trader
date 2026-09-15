with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(r"sym + \' stock market\'", 'sym + " stock market"')
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("app.py f-string fixed.")

