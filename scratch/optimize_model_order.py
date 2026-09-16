with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_models = '''AVAILABLE_AI_MODELS = list(dict.fromkeys([
    "gemini-3.8-flash-high",
    "gemini-3.8-flash",
    "gemini-3.6-flash-high",
    "gemini-3.6-flash",
    os.getenv("GEMINI_MODEL", "gemini-3.8-flash-high"),
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "antigravity-deep-trader"
]))'''

new_models = '''AVAILABLE_AI_MODELS = list(dict.fromkeys([
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-2.5-pro",
    "gemini-1.5-pro",
    "gemini-3.8-flash-high",
    "gemini-3.8-flash",
    "antigravity-deep-trader"
]))'''

if old_models in text:
    text = text.replace(old_models, new_models)
    print("Updated AVAILABLE_AI_MODELS with fast verified models first")
else:
    print("old_models not matched directly")

# In gemini_text, make timeout 4 seconds
text = text.replace("resp = requests.post(url, headers=headers, json=body, timeout=5)", "resp = requests.post(url, headers=headers, json=body, timeout=4)")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("app.py updated with model priority")

