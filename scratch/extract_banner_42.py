import zipfile, sys

with zipfile.ZipFile(r'c:\Users\SantoshMadnani\Documents\CA_Trader\42.zip') as z:
    t = z.read('terminal.html').decode('utf-8', errors='ignore')

pos = t.find('id="chartRecoBanner"')
end = t.find('id="chartRecoEvidenceSection"', pos)
with open('scratch/banner_42.txt', 'w', encoding='utf-8') as out:
    out.write(t[pos-30:end])
print("Done, length:", len(t[pos-30:end]))

