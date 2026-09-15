content = open('terminal.html', encoding='utf-8', errors='ignore').read()
p = content.find('adminFundTransferCard')
print('adminFundTransferCard found at:', p)
if p != -1:
    print(content[p-50:p+800].encode('ascii', errors='replace').decode())

