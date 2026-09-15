with open('terminal.html', encoding='utf-8', errors='ignore') as f:
    text = f.read()

p = 291136
print(text[p-1500:p-500].encode('ascii', errors='replace').decode())

