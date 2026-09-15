import sys; sys.stdout.reconfigure(encoding='utf-8')
import re
with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Check recoSettingsPopover
pos = text.find('recoSettingsPopover')
if pos != -1:
    line = text[:pos].count('\n') + 1
    print(f'recoSettingsPopover found at line {line}')
else:
    print('recoSettingsPopover NOT FOUND')

# Check lot size badge
pos2 = text.find('chartRecoLotSize')
if pos2 != -1:
    line2 = text[:pos2].count('\n') + 1
    print(f'chartRecoLotSize found at line {line2}')

# Check panel-dashboard div balance precisely
pd_start = text.find('<div class="panel active" id="panel-dashboard">')
pd_end = text.find('<div class="panel" id="panel-charts">')
chunk = text[pd_start:pd_end]
opens = len(re.findall(r'<div\b', chunk))
closes = len(re.findall(r'</div', chunk))
print(f'panel-dashboard: open={opens} close={closes} diff={opens-closes}')

# The settings popover adds a new div inside head-actions, so dashboard opens go up
# It's now showing diff=1 which means there's 1 unclosed div in dashboard
# The recoSettingsPopover outer div is inside head-actions which is in page-head which is in panel-dashboard
# That's correct since the popover is inside the panel. We need to find if it closes properly
pp_start = text.find('id="recoSettingsPopover"')
if pp_start != -1:
    # Find the closing tag
    after = text[pp_start:pp_start+500]
    divs_open = len(re.findall(r'<div\b', after))
    divs_close = len(re.findall(r'</div', after))
    print(f'recoSettingsPopover region: open={divs_open} close={divs_close}')
    print('snippet:', text[pp_start:pp_start+300])
