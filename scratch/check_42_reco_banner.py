import zipfile

with zipfile.ZipFile(r'c:\Users\SantoshMadnani\Documents\CA_Trader\42.zip') as z:
    text = z.read('terminal.html').decode('utf-8', errors='ignore')

pos = text.find('id="chartRecoBanner"')
print("chartRecoBanner starts at", pos)
# find closing
end = text.find('id="chartRecoEvidenceSection"')
print("chartRecoEvidenceSection starts at", end)
print(text[pos-50:end])
