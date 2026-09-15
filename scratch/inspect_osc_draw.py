content = open('terminal.html', encoding='utf-8', errors='ignore').read()
p = content.find('isOscillator')
print(content[p:p+1500].encode('ascii', errors='replace').decode())

