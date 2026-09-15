import zipfile, re
with zipfile.ZipFile(r'c:\Users\SantoshMadnani\Documents\CA_Trader\42.zip') as z:
    content = z.read('terminal.html').decode('utf-8', errors='ignore')

panels = list(re.finditer(r'<div[^>]*id=["\'](panel-[^"\']+)["\'][^>]*>', content))
for p in panels:
    print(p.group(1), "at", p.start())

