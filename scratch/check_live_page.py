import subprocess, time, json, urllib.request, asyncio, websockets, os

PORT_CHROME = 9299
chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

proc = subprocess.Popen([
    chrome_path,
    "--headless=new",
    f"--remote-debugging-port={PORT_CHROME}",
    "--disable-gpu",
    "--disable-extensions",
    "about:blank"
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

for _ in range(10):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT_CHROME}/json/list") as resp:
            targets = json.loads(resp.read().decode())
            break
    except Exception:
        time.sleep(0.5)

page_target = next(t for t in targets if t.get("type") == "page")
ws_url = page_target["webSocketDebuggerUrl"]

try:
    async def run():
        async with websockets.connect(ws_url) as ws:
            mid = 1
            async def call(method, params=None):
                nonlocal mid
                mid += 1
                cur_id = mid
                await ws.send(json.dumps({"id": cur_id, "method": method, "params": params or {}}))
                while True:
                    d = json.loads(await ws.recv())
                    if d.get("id") == cur_id:
                        return d

            async def listen():
                try:
                    while True:
                        msg = json.loads(await ws.recv())
                        method = msg.get("method", "")
                        if "exception" in method.lower():
                            details = msg.get("params", {}).get("exceptionDetails", {})
                            print(">>> LIVE EXCEPTION:", details.get("text"), details.get("exception", {}).get("description"), "line:", details.get("lineNumber"), "col:", details.get("columnNumber"), "url:", details.get("url"))
                        elif "console" in method.lower():
                            args = [str(a.get("value", a.get("description", ""))) for a in msg.get("params", {}).get("args", [])]
                            if msg.get("params", {}).get("type") in ["error", "warning"]:
                                print("LIVE CONSOLE:", msg.get("params", {}).get("type"), " ".join(args[:5]))
                except asyncio.CancelledError:
                    pass

            await call("Runtime.enable")
            await call("Page.enable")
            await call("Log.enable")
            
            # Step 1: Login
            await call("Page.navigate", {"url": "https://catrader.site/login"})
            await asyncio.sleep(2)

            login_js = """
            (async () => {
                const res = await fetch('/api/auth/login', {
                    method: 'POST',
                    credentials: 'include',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({email: 'santoshmadnani@catrader.site', password: 'Trader@123'})
                });
                return await res.json();
            })()
            """
            await call("Runtime.evaluate", {"expression": login_js, "awaitPromise": True, "returnByValue": True})

            # Step 2: Navigate to terminal with active exception listener
            listener = asyncio.create_task(listen())
            print("Navigating to terminal with live error listener...")
            # Step 2: Navigate to terminal
            await call("Page.navigate", {"url": "https://catrader.site/terminal"})
            await asyncio.sleep(6)
            listener.cancel()

            print("Done capturing terminal load events!")
            checks = {
                "Title": "document.title",
                "Market Clock": "document.getElementById('marketClock')?.textContent",
                "Watchlist Count": "document.querySelectorAll('.wl-item').length",
                "Watchlist Symbols": "Array.from(document.querySelectorAll('.wl-item')).map(x => x.dataset.symbol)",
                "Selected Instrument": "window.CATraderSymbol || document.getElementById('chartSymbolTitle')?.textContent",
                "Company Name": "document.getElementById('chartCompanyName')?.textContent",
                "Thesis Signal Badge": "document.getElementById('msSignalBadge')?.textContent",
                "Thesis Headline": "document.getElementById('msThesisHeadline')?.textContent",
                "Thesis Narrative": "document.getElementById('msThesisNarrative')?.textContent",
                "Pillar 1 Tech": "document.getElementById('msPillarTech')?.textContent",
                "Pillar 2 Greeks": "document.getElementById('msPillarGreeks')?.textContent",
                "Pillar 3 Flow": "document.getElementById('msPillarFlow')?.textContent",
                "Pillar 4 News": "document.getElementById('msPillarNews')?.textContent",
                "Chart Candles Count": "window.state?.candles?.length || 0"
            }
            results = {}
            for label, expr in checks.items():
                res = await call("Runtime.evaluate", {"expression": expr, "returnByValue": True})
                results[label] = res.get("result", {}).get("result", {}).get("value")

            print(json.dumps(results, indent=2))

    asyncio.run(run())
finally:
    proc.terminate()
