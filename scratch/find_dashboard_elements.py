import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('terminal.html', encoding='utf-8') as f:
    text = f.read()

def find_block(id_str):
    pos = text.find(f'id="{id_str}"')
    if pos == -1:
        print(f"NOT FOUND: {id_str}")
        return
    print(f"FOUND: {id_str} at {pos}")
    # print up to next 100 chars
    print(text[pos:pos+150])

for target in [
    'chartRecoBanner',
    'masterSummaryCard',
    'recoRationaleCard',
    'chartGreeksGrid',
    'chartPriceSensitivityCard',
    'panel-reco',
    'recommendationHistory',
    'panel-auto'
]:
    find_block(target)
