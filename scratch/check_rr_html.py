import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    content = f.read()
lines = content.split('\n')

for kw in ['recoRationaleTechnicals', 'recoRationaleNews', 'recoRationaleGreeks', 
           'recoRationalePatterns', 'recoRationaleOtherFactors', 'recoRationaleSignalTag',
           'recoTechConfluenceCount', 'recoRationaleGreeksContract']:
    idx = content.find(f'id="{kw}"')
    if idx < 0:
        print(f'NOT IN HTML: {kw}')
    else:
        ln = content[:idx].count('\n') + 1
        print(f'HTML OK at line {ln}: {kw}')

# Also find where updateRecommendationRationale is called from renderChartRecoData
idx_rr = content.find('updateRecommendationRationale(rec, baseSym)')
if idx_rr < 0:
    idx_rr = content.find('updateRecommendationRationale(reco, baseSym)')
if idx_rr >= 0:
    ln = content[:idx_rr].count('\n') + 1
    print(f'\nupdateRecommendationRationale called at line {ln}')
    for i,l in enumerate(lines[max(0,ln-5):ln+5], max(0,ln-5)+1):
        print(f'  {i}: {l[:200]}')
else:
    print('\nupdateRecommendationRationale call NOT FOUND in renderChartRecoData')
