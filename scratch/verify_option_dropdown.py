import subprocess
import time
import json
import urllib.request
import asyncio
import websockets
import sys

sys.stdout.reconfigure(encoding='utf-8')

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

            await ws.send(json.dumps({"id": 100, "method": "Runtime.enable"}))
            await ws.send(json.dumps({"id": 101, "method": "Page.enable"}))
            
            await call("Page.navigate", {"url": "https://catrader.site/login"})
            await asyncio.sleep(2)

            login_js = """
            (async function() {
                const res = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    credentials: 'include',
                    body: JSON.stringify({ email: 'santoshmadnani@catrader.site', password: 'Santosh@9340925132#' })
                });
                return res.status;
            })()
            """
            await call("Runtime.evaluate", {"expression": login_js, "awaitPromise": True})

            await call("Page.navigate", {"url": "https://catrader.site/terminal"})
            await asyncio.sleep(4)

            # Test typing into option search and wait 3.5s
            test_type = """
            (function() {
                const input = document.getElementById('chartRecoOptionSearch');
                if (input) {
                    input.focus();
                    input.value = '23500 CE';
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                    return 'DISPATCHED_INPUT';
                }
                return 'INPUT_NOT_FOUND';
            })()
            """
            res = await call("Runtime.evaluate", {"expression": test_type})
            print("Dispatch result:", res.get("result", {}).get("result", {}).get("value"))

            # Wait 3.5s for search API response
            await asyncio.sleep(3.5)

            menu_check = """
            (function() {
                const menu = document.getElementById('chartRecoOptionSuggestions');
                return {
                    display: menu ? window.getComputedStyle(menu).display : null,
                    itemCount: menu?.querySelectorAll('.instrument-suggestion')?.length,
                    items: Array.from(menu?.querySelectorAll('.instrument-suggestion') || []).slice(0, 5).map(el => el.innerText.trim().replace(/\\n+/g, ' | ')),
                    htmlSample: menu?.innerHTML?.slice(0, 300)
                };
            })()
            """
            res = await call("Runtime.evaluate", {"expression": menu_check, "returnByValue": True})
            print("Option Dropdown Result after 3.5s:\n", json.dumps(res.get("result", {}).get("result", {}).get("value"), indent=2))

    asyncio.run(run())
finally:
    proc.terminate()

