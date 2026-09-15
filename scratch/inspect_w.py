with open('terminal.html', encoding='utf-8', errors='ignore') as f:
    text = f.read()

p = 297142
print(text[p-500:p+300].encode('ascii', errors='replace').decode())

