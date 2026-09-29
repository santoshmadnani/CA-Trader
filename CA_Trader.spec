# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:/Users/SantoshMadnani/OneDrive - BDO INDIA SERVICES PRIVATE LIMITED/Personal files/CA_Trader/app/desktop_app.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['webview', 'webview.platforms.winforms', 'clr', 'pythonnet'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CA_Trader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:/Users/SantoshMadnani/OneDrive - BDO INDIA SERVICES PRIVATE LIMITED/Personal files/CA_Trader/app/static/ca_trader.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CA_Trader',
)
