import zipfile
import os
import pathlib
import sys

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE = pathlib.Path(r'c:\Users\SantoshMadnani\Documents\CA_Trader\7')
ZIP_OUT_1 = pathlib.Path(r'c:\Users\SantoshMadnani\Documents\CA_Trader\46.zip')
ZIP_OUT_2 = BASE / '46.zip'

FILES = [
    'app.py',
    'CA_Trader_Login.html',
    'Dockerfile',
    'fitness.html',
    'requirements.txt',
    'terminal.html',
    'terminal_selector.html',
]

print("=== Building 46.zip for Manual Deployment ===")

for zip_dest in [ZIP_OUT_1, ZIP_OUT_2]:
    print(f"\nPackaging {zip_dest} ...")
    with zipfile.ZipFile(zip_dest, 'w', zipfile.ZipDeflated if hasattr(zipfile, 'ZipDeflated') else zipfile.ZIP_DEFLATED) as zf:
        for fname in FILES:
            fpath = BASE / fname
            if fpath.exists():
                zf.write(fpath, fname)
                size = fpath.stat().st_size
                print(f"  + {fname:25s} ({size:,} bytes)")
            else:
                print(f"  ! Missing required file: {fname}")
                sys.exit(1)
    print(f"✓ {zip_dest.name} created successfully ({os.path.getsize(zip_dest):,} bytes)")

print("\nAll files bundled and verified in 46.zip!")

