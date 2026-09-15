import subprocess
import time
import json
import urllib.request
import asyncio
import websockets
import os
import tempfile

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT_CHROME = 9241
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

            async def listen():
                try:
                    while True:
                        m = await ws.recv()
                        d = json.loads(m)
                        if d.get("method") == "Runtime.exceptionThrown":
                            exc = d["params"]["exceptionDetails"]
                            print(f">>> RUNTIME EXCEPTION at line {exc.get('lineNumber')}, col {exc.get('columnNumber')}: {exc.get('text')} - {exc.get('exception', {}).get('description')}")
                        elif d.get("method") == "Runtime.consoleAPICalled":
                            typ = d["params"]["type"]
                            args = [str(a.get("value", a.get("description", ""))) for a in d["params"]["args"]]
                            if typ in ["error", "warning"]:
                                print(f"[{typ.upper()}] " + " ".join(args[:4]))
                except asyncio.CancelledError:
                    pass

            await call("Runtime.enable")
            await call("Page.enable")

            listener = asyncio.create_task(listen())
            
            url = f"file:///{os.path.abspath('terminal.html').replace(os.sep, '/')}"
            await call("Page.navigate", {"url": url})
            await asyncio.sleep(4)
            listener.cancel()

            checks = [
                "document.title",
                "typeof window.A",
                "typeof window.__CA_TRADER_STATE",
                "typeof window.onSymbolChanged",
                "typeof window.W0",
                "window.CATraderSymbol"
            ]
            for c in checks:
                res = await call("Runtime.evaluate", {"expression": c, "returnByValue": True})
                print(f"`{c}` =>", res.get("result", {}).get("result", {}).get("value"))

    asyncio.run(run())
finally:
    proc.terminate()

