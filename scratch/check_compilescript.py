import subprocess
import time
import json
import urllib.request
import asyncio
import websockets

PORT_CHROME = 9272
chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
proc = subprocess.Popen([
    chrome_path,
    "--headless=new",
    f"--remote-debugging-port={PORT_CHROME}",
    "--disable-gpu",
    "about:blank"
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

time.sleep(2)

try:
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT_CHROME}/json/list") as resp:
        targets = json.loads(resp.read().decode())
    ws_url = targets[0]["webSocketDebuggerUrl"]

    async def run():
        async with websockets.connect(ws_url) as ws:
            mid = 1
            async def call(method, params=None):
                nonlocal mid
                mid += 1
                cur_id = mid
                await ws.send(json.dumps({"id": cur_id, "method": method, "params": params or {}}))
                while True:
                    d = json.loads(await ws.recv())
                    if d.get("id") == cur_id:
                        return d

            await call("Runtime.enable")
            
            with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            import re
            scripts = re.findall(r'<script\b[^>]*>(.*?)</script>', content, flags=re.DOTALL | re.IGNORECASE)
            print(f"Total script tags: {len(scripts)}")
            for idx, sc in enumerate(scripts):
                res = await call("Runtime.compileScript", {
                    "expression": sc,
                    "sourceURL": f"script_{idx}.js",
                    "persistScript": False
                })
                err = res.get("result", {}).get("exceptionDetails")
                if err:
                    print(f"ERROR in Script {idx}: line {err.get('lineNumber')} - {err.get('text')}: {err.get('exception', {}).get('description')}")
                else:
                    print(f"Script {idx} (len {len(sc)}): VALID SYNTAX")

    asyncio.run(run())
finally:
    proc.terminate()

