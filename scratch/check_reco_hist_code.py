with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    text_app = f.read()

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text_term = f.read()

import re
m_app = re.search(r'def\s+recommendation_history\s*\(', text_app)
if m_app:
    idx = m_app.start()
    print("app.py recommendation_history:\n", text_app[idx:idx+1500].encode('ascii', errors='replace').decode('ascii'))

m_term = re.search(r'function\s+loadRecommendationHistory\s*\(', text_term)
if m_term:
    idx = m_term.start()
    print("terminal.html loadRecommendationHistory:\n", text_term[idx:idx+1500].encode('ascii', errors='replace').decode('ascii'))

