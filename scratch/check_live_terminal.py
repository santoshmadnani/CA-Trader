import subprocess
import time
import json
import urllib.request
import asyncio
import websockets
import os

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT_CHROME = 9239

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
            await call("Network.enable")
            
            print("Navigating to https://catrader.site/login...")
            await call("Page.navigate", {"url": "https://catrader.site/login"})
            await asyncio.sleep(2)

            # Check if login form is present
            title = await call("Runtime.evaluate", {"expression": "document.title"})
            print("Page title:", title.get("result", {}).get("result", {}).get("value"))

            # Fill in login form
            login_res = await call("Runtime.evaluate", {
                "expression": """(async () => {
                    const emailInput = document.querySelector('#pane-signin input[type="email"]') || document.querySelector('input[type="email"]') || document.getElementById('e');
                    const passInput = document.querySelector('#pane-signin input[type="password"]') || document.querySelector('input[type="password"]') || document.getElementById('p');
                    const btn = document.querySelector('#pane-signin .btn-primary') || document.querySelector('button[type="submit"]') || document.querySelector('form button');
                    
                    if (!emailInput || !passInput) return 'inputs not found';
                    
                    emailInput.value = 'santoshmadnani553@gmail.com';
                    passInput.value = 'Admin@123';
                    
                    const res = await fetch('/api/auth/login', {
                        method: 'POST',
                        credentials: 'include',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({email: emailInput.value, password: passInput.value, remember_me: true})
                    });
                    const d = await res.json();
                    return {status: res.status, body: d};
                })()""",
                "awaitPromise": True,
                "returnByValue": True
            })
            print("Login attempt:", login_res.get("result", {}).get("result", {}).get("value"))

            # Now navigate to /terminal
            print("Navigating to https://catrader.site/terminal...")
            await call("Page.navigate", {"url": "https://catrader.site/terminal"})
            await asyncio.sleep(3)

            # Check terminal status and panels!
            term_res = await call("Runtime.evaluate", {
                "expression": """(() => {
                    const title = document.title;
                    const url = location.href;
                    const panels = Array.from(document.querySelectorAll('.panel')).map(p => ({
                        id: p.id,
                        classes: p.className,
                        parentTag: p.parentElement.tagName,
                        parentClass: p.parentElement.className,
                        display: window.getComputedStyle(p).display,
                        height: p.offsetHeight
                    }));
                    return {title, url, panels};
                })()""",
                "returnByValue": True
            })
            print("Terminal on production:", json.dumps(term_res.get("result", {}).get("result", {}).get("value"), indent=2))

    asyncio.run(run())
finally:
    proc.terminate()

