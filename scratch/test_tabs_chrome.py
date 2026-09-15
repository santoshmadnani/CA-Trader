import subprocess
import time
import json
import urllib.request
import asyncio
import websockets
import os

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT_CHROME = 9229

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
            
            # Let's test locally by reading file:/// or http://
            url = f"file:///{os.path.abspath('terminal.html').replace(os.sep, '/')}"
            print("Loading local terminal:", url)
            await call("Page.navigate", {"url": url})
            await asyncio.sleep(3)

            # Check navtab count and names
            tabs = await call("Runtime.evaluate", {
                "expression": "Array.from(document.querySelectorAll('.navtab')).map(t => ({tab: t.dataset.tab, text: t.innerText.trim(), offsetParent: !!t.offsetParent}))",
                "returnByValue": True
            })
            print("Tabs found:", tabs.get("result", {}).get("result", {}).get("value"))

            # Now try clicking each tab
            test_tabs = ['options', 'news', 'fundamentals', 'movers', 'other-factors', 'reco', 'orders', 'funds']
            for tname in test_tabs:
                res = await call("Runtime.evaluate", {
                    "expression": f"""(() => {{
                        const tabEl = document.querySelector('.navtab[data-tab="{tname}"]');
                        if (!tabEl) return 'tab element not found';
                        tabEl.click();
                        const panel = document.getElementById('panel-{tname}');
                        if (!panel) return 'panel element not found';
                        const style = window.getComputedStyle(panel);
                        return {{
                            tabActive: tabEl.classList.contains('active'),
                            panelActive: panel.classList.contains('active'),
                            display: style.display,
                            visibility: style.visibility,
                            height: panel.offsetHeight,
                            children: panel.children.length
                        }};
                    }})()""",
                    "returnByValue": True
                })
                print(f"Click tab '{tname}':", res.get("result", {}).get("result", {}).get("value"))

    asyncio.run(run())
finally:
    proc.terminate()

