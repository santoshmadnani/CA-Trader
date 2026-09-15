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
PORT_CHROME = 9270

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

            # Check /login or perform login
            print("Navigating to https://catrader.site ...")
            await call("Page.navigate", {"url": "https://catrader.site"})
            await asyncio.sleep(2)

            curr_url = await call("Runtime.evaluate", {
                "expression": "window.location.href",
                "returnByValue": True
            })
            print("Current URL:", curr_url.get("result", {}).get("result", {}).get("value"))

            # Log in using credentials
            login_res = await call("Runtime.evaluate", {
                "expression": """
                (async () => {
                    const u = document.querySelector('input[type="text"], input[name="username"], #username');
                    const p = document.querySelector('input[type="password"], input[name="password"], #password');
                    const btn = document.querySelector('button[type="submit"], .btn-login, #loginBtn') || Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Login'));
                    if (u && p && btn) {
                        u.value = 'admin';
                        p.value = 'admin123';
                        btn.click();
                        return { action: 'clicked login' };
                    }
                    return { action: 'already on app or no login fields' };
                })()
                """,
                "awaitPromise": True,
                "returnByValue": True
            })
            print("Login attempt:", login_res.get("result", {}).get("result", {}).get("value"))
            await asyncio.sleep(4)

            curr_url2 = await call("Runtime.evaluate", {
                "expression": "window.location.href",
                "returnByValue": True
            })
            print("URL after login:", curr_url2.get("result", {}).get("result", {}).get("value"))

            # Now check terminal elements
            user_res = await call("Runtime.evaluate", {
                "expression": "document.getElementById('userDisplayName')?.textContent",
                "returnByValue": True
            })
            print("User display name on live site:", user_res.get("result", {}).get("result", {}).get("value"))

            dash_eval = await call("Runtime.evaluate", {
                "expression": """
                (async () => {
                    if (typeof showTab === 'function') showTab('dashboard');
                    if (typeof window.loadDashboard === 'function') await window.loadDashboard();
                    return {
                        symbolTitle: document.getElementById('dashSymbolTitle')?.textContent,
                        symbolLtp: document.getElementById('dashSymbolLtp')?.textContent,
                        confluenceRows: document.querySelectorAll('#dashConfluenceTableBody tr').length,
                        entryRationale: document.getElementById('dashEntryPriceDisplay')?.textContent,
                        slRationale: document.getElementById('dashSlPriceDisplay')?.textContent,
                        targetRationale: document.getElementById('dashTargetPriceDisplay')?.textContent,
                        simSliderExists: !!document.getElementById('chartSimSlider'),
                        simDeltaDisplay: document.getElementById('chartSimDeltaImpact')?.textContent
                    };
                })()
                """,
                "awaitPromise": True,
                "returnByValue": True
            })
            print("Dashboard evaluation on live site:")
            print(json.dumps(dash_eval.get("result", {}).get("result", {}).get("value"), indent=2))

    asyncio.run(run())

finally:
    proc.kill()

