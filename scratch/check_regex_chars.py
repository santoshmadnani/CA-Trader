with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    c = f.read()

p = c.find('const isAlreadyOption =')
print(repr(c[p:p+300]))

