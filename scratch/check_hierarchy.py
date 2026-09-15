import subprocess
import time
import json
import urllib.request
import asyncio
import websockets
import os

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT_CHROME = 9232

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
            
            url = f"file:///{os.path.abspath('terminal.html').replace(os.sep, '/')}"
            await call("Page.navigate", {"url": url})
            await asyncio.sleep(2)

            res = await call("Runtime.evaluate", {
                "expression": """(() => {
                    function getHierarchy(el) {
                        const path = [];
                        let curr = el;
                        while (curr && curr !== document.body) {
                            path.push({
                                tag: curr.tagName,
                                id: curr.id,
                                cls: curr.className,
                                display: window.getComputedStyle(curr).display
                            });
                            curr = curr.parentElement;
                        }
                        return path;
                    }
                    return {
                        charts: getHierarchy(document.getElementById('panel-charts')),
                        news: getHierarchy(document.getElementById('panel-news')),
                        options: getHierarchy(document.getElementById('panel-options')),
                        movers: getHierarchy(document.getElementById('panel-movers')),
                        funds: getHierarchy(document.getElementById('panel-funds')),
                    };
                })()""",
                "returnByValue": True
            })
            print(json.dumps(res.get("result", {}).get("result", {}).get("value"), indent=2))

    asyncio.run(run())
finally:
    proc.terminate()

