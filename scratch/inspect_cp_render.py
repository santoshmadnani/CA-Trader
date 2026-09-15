content = open('terminal.html', encoding='utf-8', errors='ignore').read()
p = content.find("$('chartPatternList').innerHTML")
print(content[p-50:p+500].encode('ascii', errors='replace').decode())

