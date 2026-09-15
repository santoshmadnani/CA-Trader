with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

funcs = [
    'loadDashboard', 'loadChart', 'loadOptions', 'loadNewsByCaAi',
    'loadFundamentals', 'loadOtherFactorsSuite', 'loadMovers',
    'loadPortfolioSnapshot', 'loadFundsTab'
]
for fn in funcs:
    has_fn = f"function {fn}" in text or f"{fn} =" in text
    print(f"{fn:25}: {has_fn}")

