import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    c = f.read()

p = c.find('@app.get("/api/instruments/search")')
print(c[p:p+700])

