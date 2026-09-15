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
PORT_CHROME = 9248

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
            exceptions = []
            console_logs = []

            async def call(method, params=None):
                nonlocal mid
                mid += 1
                cur_id = mid
                await ws.send(json.dumps({"id": cur_id, "method": method, "params": params or {}}))
                while True:
                    m = await ws.recv()
                    d = json.loads(m)
                    if d.get("method") == "Runtime.exceptionThrown":
                        exceptions.append(d["params"]["exceptionDetails"])
                    elif d.get("method") == "Runtime.consoleAPICalled":
                        console_logs.append(d["params"])
                    elif d.get("id") == cur_id:
                        return d

            await call("Runtime.enable")
            await call("Page.enable")
            
            url = f"file:///{os.path.abspath('terminal.html').replace(os.sep, '/')}"
            print("Navigating to:", url)
            await call("Page.navigate", {"url": url})
            
            # Wait 3 seconds and gather events
            for _ in range(30):
                await asyncio.sleep(0.1)
                try:
                    m = await asyncio.wait_for(ws.recv(), timeout=0.05)
                    d = json.loads(m)
                    if d.get("method") == "Runtime.exceptionThrown":
                        exceptions.append(d["params"]["exceptionDetails"])
                except asyncio.TimeoutError:
                    pass

            print(f"Total exceptions captured: {len(exceptions)}")
            for idx, ex in enumerate(exceptions):
                print(f"Exception #{idx+1}: {ex.get('text')} at {ex.get('url')}:{ex.get('lineNumber')}:{ex.get('columnNumber')}")
                print("Details:", ex.get("exception", {}).get("description"))

    asyncio.run(run())

finally:
    proc.kill()

