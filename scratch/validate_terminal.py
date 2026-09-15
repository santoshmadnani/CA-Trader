import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Check that open and close script tags match
opens = len(re.findall(r'<script\b', content, re.IGNORECASE))
closes = len(re.findall(r'</script>', content, re.IGNORECASE))
print(f"Script tags: {opens} open, {closes} close")
assert opens == closes, f"Mismatch in script tags: {opens} != {closes}"

# Check for major elements
required_ids = [
    'chartModeToggle', 'chartAiPanel', 'chartAiApplyAllBtn',
    'panel-backtest', 'btCanvas', 'btPlayPauseBtn', 'btStepBtn', 'btResetBtn',
    'btTimelineSlider', 'btSignalBadge', 'btPositionsTableBody',
    'panel-reco', 'subTabActiveRecos', 'subTabRecoHistory', 'recoSessionTitle',
    'recoNextMarketDayBadge', 'recoCalculationModal', 'recoCalcModalClose',
    'autoAddSymbolBtn', 'autoSymbolSuggestions', 'autoMaxLoss', 'autoMaxProfit',
    'editUIBtn', 'caToggleCompactButtons', 'caResetLayout', 'caEditDone'
]

for rid in required_ids:
    if f'id="{rid}"' in content or f"id='{rid}'" in content:
        print(f"✓ id='{rid}' found")
    else:
        print(f"✗ id='{rid}' MISSING!")

# Check python py_compile on app.py
import subprocess
res = subprocess.run([sys.executable, '-m', 'py_compile', 'app.py'], capture_output=True, text=True)
if res.returncode == 0:
    print("✓ app.py compiles cleanly (100% valid Python)")
else:
    print(f"✗ app.py compilation error: {res.stderr}")

print("Validation check finished.")

