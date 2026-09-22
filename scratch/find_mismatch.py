import re
with open('static/js/features/terminal_core_features.js', 'r', encoding='utf-8') as f:
    code = f.read()
from bs4 import BeautifulSoup

with open('terminal.html', 'r', encoding='utf-8') as f:
    html = f.read()
lines = code.splitlines()
with open('terminal.html', 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

scripts_with_pos = []
for m in re.finditer(r'<script\b[^>]*>(.*?)</script>', html, re.DOTALL):
    scripts_with_pos.append((m.start(), m.end(), m.group(1)))
# We can use binary search with Chrome V8 Runtime.compileScript to pinpoint the exact line where syntax breaks!
import subprocess, time, json, urllib.request, websockets, asyncio
soup = BeautifulSoup(content, 'html.parser')
scripts = soup.find_all('script')
s16_code = scripts[15].get_text()
lines = s16_code.splitlines()

sp6, ep6, s6 = scripts_with_pos[6]
base_line = html[:sp6].count('\n') + 1
print(f"Script 6 starts at line {base_line}, len={len(s6)}")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 9330
stack = []
in_str = False
str_char = ''
in_block_comment = False

# Find unmatched ) - more ) than (
depth = 0
all_opens = []
unmatched_closes = []
for i, c in enumerate(s6):
    if c == '(':
        depth += 1
        all_opens.append(i)
    elif c == ')':
        depth -= 1
        if depth < 0:
            unmatched_closes.append(i)
            depth = 0
        elif all_opens:
            all_opens.pop()
proc = subprocess.Popen([
    CHROME,
    "--headless=new",
    f"--remote-debugging-port={PORT}",
    "--disable-gpu",
    "about:blank"
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
for line_idx, line in enumerate(lines, 1):
    i = 0
    while i < len(line):
        ch = line[i]
        if in_block_comment:
            if ch == '*' and i + 1 < len(line) and line[i+1] == '/':
                in_block_comment = False
                i += 1
        elif in_str:
            if ch == '\\':
                i += 1
            elif ch == str_char:
                in_str = False
        else:
            if ch == '/' and i + 1 < len(line) and line[i+1] == '/':
                break
            elif ch == '/' and i + 1 < len(line) and line[i+1] == '*':
                in_block_comment = True
                i += 1
            elif ch in ('"', "'", '`'):
                in_str = True
                str_char = ch
            elif ch == '{':
                stack.append((line_idx, line.strip()[:60]))
            elif ch == '}':
                if stack:
                    stack.pop()
        i += 1

print(f"Unmatched ) positions: {unmatched_closes}")
print(f"Unmatched ( positions (remaining opens): {all_opens}")
for pos in unmatched_closes[:10]:
    file_line = base_line + s6[:pos].count('\n')
    context = s6[max(0,pos-100):pos+100]
    print(f"\nFile line ~{file_line}, offset={pos}")
    print(f"  context: {repr(context)}")
for pos in all_opens[:10]:
    file_line = base_line + s6[:pos].count('\n')
    context = s6[max(0,pos-100):pos+100]
    print(f"\nOpen paren at file line ~{file_line}, offset={pos}")
    print(f"  context: {repr(context)}")
time.sleep(2)

async def check():
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list") as resp:
            targets = json.loads(resp.read().decode())
        page = next(t for t in targets if t.get("type") == "page")
        async with websockets.connect(page["webSocketDebuggerUrl"]) as ws:
            mid = 0
            async def call(method, params=None):
                nonlocal mid
                mid += 1
                cur_id = mid
                await ws.send(json.dumps({"id": cur_id, "method": method, "params": params or {}}))
                while True:
                    m = await ws.recv()
                    d = json.loads(m)
                    if d.get("id") == cur_id:
                        return d

            await call("Runtime.enable")

            # Let's inspect line by line or chunk by chunk
            res = await call("Runtime.compileScript", {
                "expression": code,
                "sourceURL": "test.js",
                "persistScript": False
            })
            print("Full compile error:", res.get("result", {}).get("exceptionDetails"))
    finally:
        proc.terminate()

asyncio.run(check())
print(f"Unclosed braces count: {len(stack)}")
for item in stack:
    print(f"Line {item[0]}: {item[1]}")
