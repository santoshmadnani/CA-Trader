with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = 920860
print(text[idx:idx+2500].encode('ascii', errors='replace').decode('ascii'))

