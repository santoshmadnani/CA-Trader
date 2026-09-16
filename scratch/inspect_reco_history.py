import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('app.py', 'r', encoding='utf-8') as f:
    app_text = f.read()

import re
print("Matches in app.py:")
for m in re.finditer(r'.{0,60}(?:recommendation_history|save_recommendation|reco_history).{0,60}', app_text):
    print(' ', m.group(0))

with open('terminal.html', 'r', encoding='utf-8') as f:
    term_text = f.read()

print("\nMatches in terminal.html:")
for m in re.finditer(r'.{0,60}(?:recommendation_history|addToRecoHistory|saveRecommendation|loadRecommendationHistory).{0,60}', term_text):
    print(' ', m.group(0))

