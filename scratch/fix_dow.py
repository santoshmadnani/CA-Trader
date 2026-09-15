with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()
text = text.replace('52,051.04 (+0.31%)', '40,920.40 (-0.45%)')
text = text.replace('<div>Dow: <b style="color:var(--buy);">40,920.40 (-0.45%)</b></div>', '<div>Dow: <b style="color:var(--sell);">40,920.40 (-0.45%)</b></div>')
with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(text)
print('Replaced DOW in terminal.html')

