import subprocess, time, json, urllib.request, asyncio, websockets, sys

sys.stdout.reconfigure(encoding='utf-8')

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT_CHROME = 9225

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

            # Login
            await call("Page.navigate", {"url": "https://catrader.site/login"})
            await asyncio.sleep(2)
            await call("Runtime.evaluate", {
                "expression": """
                fetch('/api/auth/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    credentials: 'include',
                    body: JSON.stringify({email: 'santoshmadnani@catrader.site', password: 'Santosh@9340925132#'})
                })
                """,
                "awaitPromise": True
            })

            # Go to terminal
            await call("Page.navigate", {"url": "https://catrader.site/terminal"})
            await asyncio.sleep(5)

            # Test calling applyOptionRecommendation directly
            direct_test = await call("Runtime.evaluate", {
                "expression": """
                (() => {
                    try {
                        // Underlying is Bearish (NIFTY 23400 PE was default).
                        // Calling with Call option -> Should trigger Counter-Trend advisory!
                        applyOptionRecommendation('NIFTY 23500 CE', 95.0, 'NIFTY');
                        return {
                            success: true,
                            action: document.getElementById('chartRecoAction')?.textContent,
                            symbol: document.getElementById('chartRecoSymbol')?.textContent,
                            advisoryIcon: document.getElementById('chartRecoAdvisoryIcon')?.textContent,
                            advisoryText: document.getElementById('chartRecoAdvisoryText')?.textContent,
                            entry: document.getElementById('chartRecoEntry')?.textContent,
                            target: document.getElementById('chartRecoTgt')?.textContent,
                            sl: document.getElementById('chartRecoSl')?.textContent
                        };
                    } catch(e) {
                        return { error: e.message, stack: e.stack };
                    }
                })()
                """,
                "returnByValue": True
            })
            print("Direct applyOptionRecommendation (Counter-Trend Call in Bear Market):")
            print(json.dumps(direct_test.get("result", {}).get("result", {}).get("value"), indent=2))

            # Test calling applyOptionRecommendation with OTM Put (Aligned in Bear Market)
            otm_test = await call("Runtime.evaluate", {
                "expression": """
                (() => {
                    try {
                        // Calling with OTM Put -> Should qualify as BUY with Budget-Friendly OTM advisory!
                        applyOptionRecommendation('NIFTY 22900 PE', 45.0, 'NIFTY');
                        return {
                            success: true,
                            action: document.getElementById('chartRecoAction')?.textContent,
                            symbol: document.getElementById('chartRecoSymbol')?.textContent,
                            advisoryIcon: document.getElementById('chartRecoAdvisoryIcon')?.textContent,
                            advisoryText: document.getElementById('chartRecoAdvisoryText')?.textContent,
                            entry: document.getElementById('chartRecoEntry')?.textContent,
                            target: document.getElementById('chartRecoTgt')?.textContent,
                            sl: document.getElementById('chartRecoSl')?.textContent
                        };
                    } catch(e) {
                        return { error: e.message, stack: e.stack };
                    }
                })()
                """,
                "returnByValue": True
            })
            print("\nDirect applyOptionRecommendation (Budget OTM Put in Bear Market):")
            print(json.dumps(otm_test.get("result", {}).get("result", {}).get("value"), indent=2))

            # Test change event on select
            change_test = await call("Runtime.evaluate", {
                "expression": """
                (() => {
                    const sel = document.getElementById('chartRecoOptionSelect');
                    if(!sel) return { error: 'No select element' };
                    sel.value = 'NIFTY 23500 CE';
                    sel.dispatchEvent(new Event('change'));
                    return {
                        selectValue: sel.value,
                        symbolNow: document.getElementById('chartRecoSymbol')?.textContent,
                        actionNow: document.getElementById('chartRecoAction')?.textContent,
                        advisoryNow: document.getElementById('chartRecoAdvisoryText')?.textContent
                    };
                })()
                """,
                "returnByValue": True
            })
            print("\nChange event dispatch test:")
            print(json.dumps(change_test.get("result", {}).get("result", {}).get("value"), indent=2))

    asyncio.run(run())
finally:
    proc.terminate()

