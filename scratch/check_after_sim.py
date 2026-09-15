import zipfile, sys
sys.stdout.reconfigure(encoding='utf-8')

with zipfile.ZipFile(r'c:\Users\SantoshMadnani\Documents\CA_Trader\42.zip') as z:
    text = z.read('terminal.html').decode('utf-8', errors='ignore')

p_sim = text.find('id="chartPriceSensitivityCard"')
# print 1500 chars after p_sim
print(text[p_sim+2000:p_sim+3500])

