import re

with open('terminal.html', 'r', encoding='utf-8') as f:
    html = f.read()

scripts = re.findall(r'<script\b[^>]*>([\s\S]*?)</script>', html)
print(f"Found {len(scripts)} script tags")

for i, s in enumerate(scripts):
    print(f"Script {i}: length = {len(s):,} characters")
    # write to temp file
    with open(f"scratch/temp_script_{i}.js", "w", encoding="utf-8") as out:
        out.write(s)

print("Wrote scripts to scratch/temp_script_*.js")

