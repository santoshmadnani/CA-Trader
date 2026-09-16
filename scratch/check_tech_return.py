import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    app = f.read()

idx = app.find('def technical_analysis(')
end = app.find('def ', idx + 10)
print(app[idx+1800:end])

