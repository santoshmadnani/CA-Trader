content = open('terminal.html', encoding='utf-8', errors='ignore').read()
p = content.find('oscPlotH')
print('oscPlotH found at:', p)
if p != -1:
    print(content[p-100:p+1200].encode('ascii', errors='replace').decode())

