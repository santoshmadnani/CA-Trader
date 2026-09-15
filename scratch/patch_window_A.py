import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    t = f.read()

# 1. Expose window.A globally in Script 2
target_A = "const A=async(u,o={})=>{"
if "window.A=A;" not in t:
    # Find end of A definition
    idx = t.find(target_A)
    # find closing semicolon of const A = ...;
    end_semi = t.find("finally{if(timer)clearTimeout(timer)}};", idx)
    if end_semi != -1:
        insert_pos = end_semi + len("finally{if(timer)clearTimeout(timer)}};")
        t = t[:insert_pos] + "\n  window.A = A;\n" + t[insert_pos:]
        print("1. Added window.A = A; globally ✓")
    else:
        print("1. Could not find end of const A=")
else:
    print("1. window.A already exposed ✓")

# 2. In runOptionSearch and initOptionSearchBox, ensure fallback to window.A || window.api || fetch
t = t.replace(
    "const d = await A('/api/instruments/search?q=' + encodeURIComponent(queryParam) + '&limit=20');",
    "const apiFn = window.A || window.api || (async(u,o={})=>fetch(u,{credentials:'include',...o}).then(r=>r.json())); const d = await apiFn('/api/instruments/search?q=' + encodeURIComponent(queryParam) + '&limit=25');"
)
t = t.replace(
    "const d = await A('/api/instruments/search?q=' + encodeURIComponent(queryParam) + '&limit=25');",
    "const apiFn = window.A || window.api || (async(u,o={})=>fetch(u,{credentials:'include',...o}).then(r=>r.json())); const d = await apiFn('/api/instruments/search?q=' + encodeURIComponent(queryParam) + '&limit=25');"
)
print("2. Made search option API calls robust with window.A || window.api || fetch ✓")

with open('terminal.html', 'w', encoding='utf-8') as f:
    f.write(t)
print("Saved terminal.html.")

