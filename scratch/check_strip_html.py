with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx_strip = text.find('id="dashAutoRecoStrip"')
print(text[idx_strip-50:idx_strip+800].encode('ascii', errors='replace').decode('ascii'))

