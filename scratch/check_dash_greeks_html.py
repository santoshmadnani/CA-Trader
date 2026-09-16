with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

idx = 120300
print(text[idx:idx+2500].encode('ascii', errors='replace').decode('ascii'))

