import subprocess
import time
import json
import urllib.request
import asyncio
import websockets
import re
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT_CHROME = 9229

import tempfile
temp_dir = tempfile.mkdtemp()
proc = subprocess.Popen([
    chrome_path,
    "--headless=new",
    f"--user-data-dir={temp_dir}",
    f"--remote-debugging-port={PORT_CHROME}",
    "--disable-gpu",
    "--no-first-run",
    "--no-default-browser-check",
    "about:blank"
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

time.sleep(2)

try:
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT_CHROME}/json/list") as resp:
        targets = json.loads(resp.read().decode())
    
    page_target = next(t for t in targets if t.get("type") == "page")
    ws_url = page_target["webSocketDebuggerUrl"]

    with open(r"c:\Users\SantoshMadnani\Documents\CA_Trader\7\terminal.html", "r", encoding="utf-8") as f:
        html = f.read()

    scripts = []
    for m in re.finditer(r'<script\b[^>]*>(.*?)</script>', html, re.DOTALL):
        start_line = html[:m.start()].count('\n') + 1
        scripts.append((start_line, m.group(1)))

    print(f"Extracted {len(scripts)} scripts from terminal.html")

    async def run():
        async with websockets.connect(ws_url) as ws:
            mid = 1
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

            for idx, (start_line, script_code) in enumerate(scripts):
                res = await call("Runtime.compileScript", {
                    "expression": script_code,
                    "sourceURL": f"script_{idx}.js",
                    "persistScript": False
                })
                
                result = res.get("result", {})
                exc = result.get("exceptionDetails")
                if exc:
                    line_offset = exc.get("lineNumber", 0)
                    col = exc.get("columnNumber", 0)
                    actual_line = start_line + line_offset
                    text = exc.get("text", "")
                    desc = exc.get("exception", {}).get("description", "")
                    print(f"\n=======================================================")
                    print(f"SYNTAX ERROR in Script {idx} (starts at line {start_line}):")
                    print(f"  Error at terminal.html line {actual_line}, col {col}: {text}")
                    print(f"  Description: {desc}")
                    # Print lines around the error
                    lines = script_code.split('\n')
                    for li in range(max(0, line_offset-3), min(len(lines), line_offset+4)):
                        prefix = "-> " if li == line_offset else "   "
                        print(f"  {prefix}{start_line + li}: {lines[li]}")
                    print(f"=======================================================\n")
                else:
                    script_id = result.get("scriptId")
                    print(f"Script {idx} (starts line {start_line}, len {len(script_code)}): OK (scriptId {script_id})")

    asyncio.run(run())
finally:
    proc.terminate()

