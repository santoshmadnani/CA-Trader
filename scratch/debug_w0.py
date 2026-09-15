import subprocess
import time
import json
import urllib.request
import asyncio
import websockets
import os

PORT_HTTP = 8888
PORT_CHROME = 9265

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
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
            
            url = f"http://127.0.0.1:{PORT_HTTP}/terminal.html"
            await call("Page.navigate", {"url": url})
            await asyncio.sleep(3)

            # Check what W, G, S are
            res = await call("Runtime.evaluate", {
                "expression": """(() => {
                    return {
                        G: window.__CA_WATCHLIST_GROUP,
                        items: window.__CA_WATCHLIST_GROUP?.items,
                        wlListHtml: document.getElementById('wl-list')?.innerHTML,
                        watchlistSelectHtml: document.getElementById('watchlistSelect')?.innerHTML,
                        symbol: window.selectedSymbol ? window.selectedSymbol() : null,
                        errorLogs: window.__CA_DEBUG_LOGS || []
                    };
                })()""",
                "returnByValue": True
            })
            print(json.dumps(res.get("result", {}).get("result", {}).get("value"), indent=2))

    asyncio.run(run())
finally:
    proc.terminate()

