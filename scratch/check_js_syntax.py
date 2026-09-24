import os, glob, subprocess, json, urllib.request, time, sys
import re
import sys

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 9260
with open(r'c:\Users\SantoshMadnani\OneDrive - BDO INDIA SERVICES PRIVATE LIMITED\Personal files\CA_Trader\app\terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

proc = subprocess.Popen([
    CHROME,
    "--headless=new",
    f"--remote-debugging-port={PORT}",
    "--disable-gpu",
    "--no-first-run",
    "--no-default-browser-check",
    "about:blank"
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
# Find script blocks
pattern = re.compile(r'<script\b[^>]*>(.*?)</script>', re.DOTALL)
for match_num, m in enumerate(pattern.finditer(text), 1):
    script_content = m.group(1)
    start_pos = m.start(1)
    # calculate line number of start_pos
    start_line = text[:start_pos].count('\n') + 1
    print(f"Script #{match_num} starts at line {start_line}, length {len(script_content)} chars")

time.sleep(2)

try:
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list") as resp:
        targets = json.loads(resp.read().decode())
    page_target = next(t for t in targets if t.get("type") == "page")
    ws_url = page_target["webSocketDebuggerUrl"]

    import asyncio, websockets
    async def run():
        async with websockets.connect(ws_url) as ws:
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

            js_files = glob.glob("static/**/*.js", recursive=True)
            print(f"Found {len(js_files)} JS files to check.")
            for fpath in sorted(js_files):
                with open(fpath, "r", encoding="utf-8") as f:
                    code = f.read()
                
                # Check for tags
                has_open = "<script" in code
                has_close = "</script" in code
                if has_open or has_close:
                    print(f"\n[TAG ERROR] {fpath}: contains <script or </script> tags! (open: {has_open}, close: {has_close})")

                # Test compile script via CDP
                res = await call("Runtime.compileScript", {
                    "expression": code,
                    "sourceURL": fpath.replace("\\", "/"),
                    "persistScript": False
                })
                
                if "exceptionDetails" in res.get("result", {}):
                    ex = res["result"]["exceptionDetails"]
                    print(f"\n[SYNTAX ERROR] {fpath}:")
                    print(f"  Line {ex.get('lineNumber')}, Col {ex.get('columnNumber')}: {ex.get('text')}")
                    if "exception" in ex:
                        print(f"  Description: {ex['exception'].get('description')}")
                else:
                    print(f"[OK] {fpath}")

    asyncio.run(run())
finally:
    proc.kill()

    # Check each line of script
    lines = script_content.split('\n')
    for line_idx, l in enumerate(lines, start_line):
        stripped = l.strip()
        # check for unfinished tokens
        if stripped in ["$('structureStat", "$('structureStat'", "$('structureStatus').textContent='Local"]:
            print(f"  [X] BROKEN LINE {line_idx}: {stripped}")
        if stripped.endswith("recen") or stripped.endswith("title"):
            print(f"  [X] TRUNCATED LINE {line_idx}: {stripped}")
        # check for illegal single-quote lines (not template literals ` and not double quotes)
        # in JS, single-line strings enclosed in ' cannot span multiple lines unless escaped with \
        # if a line contains an odd number of unescaped ', and does not end with \, it's a syntax error
        # BUT ignore lines inside template literals or comments!
