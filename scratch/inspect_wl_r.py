with open('terminal.html', encoding='utf-8', errors='ignore') as f:
    text = f.read()

p = 291136
print(text[p-500:p+1200].encode('ascii', errors='replace').decode())

