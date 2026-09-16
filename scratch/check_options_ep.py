with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

idx = 407800
print(text[idx:idx+2500].encode('ascii', errors='replace').decode('ascii'))

