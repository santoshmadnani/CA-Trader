with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx_dash = text.find('id="panel-dashboard"')
print(text[idx_dash+2000:idx_dash+4500].encode('ascii', errors='replace').decode('ascii'))

