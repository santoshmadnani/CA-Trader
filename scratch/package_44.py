import zipfile, os

files = ['app.py', 'CA_Trader_Login.html', 'Dockerfile', 'fitness.html', 'requirements.txt', 'terminal.html', 'terminal_selector.html']
out_zip = r'c:\Users\SantoshMadnani\Documents\CA_Trader\44.zip'

with zipfile.ZipFile(out_zip, 'w', compression=zipfile.ZIP_DEFLATED) as z:
    for f in files:
        z.write(f, arcname=f)
        print(f"Added {f} ({os.path.getsize(f)} bytes)")

print(f"Created {out_zip} ({os.path.getsize(out_zip)} bytes)")

