import subprocess
import time
import json
import urllib.request
import asyncio
import websockets
import os
import sys

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT_CHROME = 9238

proc = subprocess.Popen([
    chrome_path,
    "--headless=new",
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
            await call("Page.enable")

            for i in range(10):
                fn = f"scratch/temp_script_{i}.js"
                if not os.path.exists(fn):
                    continue
                with open(fn, "r", encoding="utf-8") as f:
                    code = f.read()

                comp_res = await call("Runtime.compileScript", {
                    "expression": code,
                    "sourceURL": f"temp_script_{i}.js",
                    "persistScript": False
                })
                err = comp_res.get("result", {}).get("exceptionDetails")
                if err:
                    print(f"ERROR in script {i}: {err.get('text')} at line {err.get('lineNumber')}, col {err.get('columnNumber')}")
                    print("Description:", err.get("exception", {}).get("description"))
                else:
                    print(f"Script {i}: OK")

    asyncio.run(run())

finally:
    proc.kill()

