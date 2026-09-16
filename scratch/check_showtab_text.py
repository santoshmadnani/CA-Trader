with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = 255477
print(text[idx:idx+800].encode('ascii', errors='replace').decode('ascii'))

