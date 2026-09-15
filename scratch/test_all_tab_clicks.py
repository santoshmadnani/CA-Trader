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
PORT_CHROME = 9280

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

            tabs = [
                'dashboard', 'charts', 'options', 'reco', 'news',
                'fundamentals', 'movers', 'other-factors', 'orders',
                'funds', 'console', 'reports'
            ]

            results = {}
            for t in tabs:
                res = await call("Runtime.evaluate", {
                    "expression": f"""
                    (() => {{
                        showTab('{t}');
                        const activePanel = document.querySelector('.panel.active');
                        const pId = activePanel ? activePanel.id : null;
                        const cardCount = activePanel ? activePanel.querySelectorAll('.card').length : 0;
                        const textLen = activePanel ? activePanel.textContent.trim().length : 0;
                        const isDisplayed = activePanel ? window.getComputedStyle(activePanel).display !== 'none' : false;
                        const rect = activePanel ? activePanel.getBoundingClientRect() : null;
                        return {{
                            targetTab: '{t}',
                            activePanelId: pId,
                            cardCount,
                            textLen,
                            isDisplayed,
                            height: rect ? rect.height : 0
                        }};
                    }})()
                    """,
                    "returnByValue": True
                })
                results[t] = res.get("result", {}).get("result", {}).get("value")

            print("Tab Switch Results:")
            print(json.dumps(results, indent=2))

    asyncio.run(run())

finally:
    proc.kill()

