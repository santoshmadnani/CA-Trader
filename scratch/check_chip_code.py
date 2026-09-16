with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

idx = 398935
print(text[idx-600:idx+600].encode('ascii', errors='replace').decode('ascii'))

