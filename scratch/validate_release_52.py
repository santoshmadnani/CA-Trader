import re, ast, sys
sys.stdout.reconfigure(encoding='utf-8')

print("1. Validating app.py AST...")
with open('app.py', 'r', encoding='utf-8') as f:
    app_text = f.read()

try:
    ast.parse(app_text)
    print("✓ app.py AST parsed cleanly!")
except Exception as e:
    print(f"✗ app.py AST error: {e}")
    sys.exit(1)

print("\n2. Validating terminal.html checks...")
with open('terminal.html', 'r', encoding='utf-8') as f:
    html = f.read()

required_ids = [
    'panel-notifications',
    'panel-api-passbook',
    'rightSideNotificationContainer',
    'floatingPositionWidget',
    'btnLockDrawings',
    'quickOrderLtp',
    'turboLoadBtn',
    'dedicatedNotifList',
    'apiPassbookLedgerBody',
    'upstoxRpmText',
    'geminiTodayTokensText'
]

for rid in required_ids:
    if f'id="{rid}"' in html or f"id='{rid}'" in html:
        print(f"✓ Found required ID: {rid}")
    else:
        print(f"✗ MISSING required ID: {rid}")
        sys.exit(1)

# Check for accidental double keywords
double_keywords = ['async async', 'function function', 'const const', 'let let', 'var var']
for dk in double_keywords:
    if dk in html:
        print(f"✗ Found illegal double keyword: '{dk}'")
        sys.exit(1)
print("✓ No illegal duplicate keywords found in terminal.html")

print("\nRelease 52 validation checks passed completely!")

