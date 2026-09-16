import re

with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

endpoints = re.findall(r'@app\.(?:get|post|put|delete)\(["\']([^"\']+)["\']', text)
ai_endpoints = [ep for ep in endpoints if 'ai' in ep.lower() or 'chat' in ep.lower()]
print(f"Total endpoints: {len(endpoints)}")
print(f"AI/Chat endpoints ({len(ai_endpoints)}):")
for ep in ai_endpoints:
    print(' ', ep)

# Check all chat or AI functions in app.py
funcs = re.findall(r'def\s+([a-zA-Z0-9_]*(?:chat|ai)[a-zA-Z0-9_]*)\s*\(', text, re.IGNORECASE)
print(f"\nFunctions with chat/ai ({len(funcs)}):")
for f in funcs:
    print(' ', f)

