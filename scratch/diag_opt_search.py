import subprocess
import time
import json
import urllib.request
import asyncio
import websockets
import sys

sys.stdout.reconfigure(encoding='utf-8')

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT_CHROME = 9230

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

            # Check what happens when calling /api/instruments/search from page context
            diag_js = """
            (async function() {
                const logs = [];
                try {
                    logs.push('1. Testing fetch /api/instruments/search?q=NIFTY 23500');
                    const r = await fetch('/api/instruments/search?q=NIFTY%2023500&limit=20');
                    logs.push('Status: ' + r.status);
                    const d = await r.json();
                    logs.push('Items returned: ' + (d.items?.length || 0));
                    if (d.items?.length) {
                        logs.push('Sample item: ' + JSON.stringify(d.items[0]));
                    }
                    
                    logs.push('2. Testing A() helper');
                    const dA = await A('/api/instruments/search?q=NIFTY%2023500&limit=20');
                    logs.push('A() returned items: ' + (dA.items?.length || 0));

                    logs.push('3. Check elements');
                    const inp = document.getElementById('chartRecoOptionSearch');
                    const box = document.getElementById('chartRecoOptionSuggestions');
                    logs.push('inp: ' + !!inp + ', box: ' + !!box);
                    logs.push('box style: ' + (box ? window.getComputedStyle(box).display : 'no box'));
                    logs.push('box innerHTML: ' + box?.innerHTML);

                    return logs;
                } catch(e) {
                    logs.push('ERROR: ' + e.message + ' stack: ' + e.stack);
                    return logs;
                }
            })()
            """
            res = await call("Runtime.evaluate", {"expression": diag_js, "awaitPromise": True, "returnByValue": True})
            print("API and DOM Diagnostics:")
            for l in res.get("result", {}).get("result", {}).get("value", []):
                print(" ", l)

    asyncio.run(run())
finally:
    proc.terminate()

