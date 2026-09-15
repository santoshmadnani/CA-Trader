import subprocess
import time
import json
import urllib.request
import asyncio
import websockets
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT_CHROME = 9228

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
    print(f"Connecting to page target: {page_target['id']}")

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
            await ws.send(json.dumps({"id": 102, "method": "Log.enable"}))
            await ws.send(json.dumps({"id": 103, "method": "Network.enable"}))
            
            print("Navigating to login page: https://catrader.site/login ...")
            await call("Page.navigate", {"url": "https://catrader.site/login"})
            await asyncio.sleep(2)

            # Check if login form is present and log in
            login_js = """
            (async function() {
                try {
                    const res = await fetch('/api/auth/login', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        credentials: 'include',
                        body: JSON.stringify({
                            email: 'santoshmadnani@catrader.site',
                            password: 'Santosh@9340925132#'
                        })
                    });
                    const data = await res.json();
                    return { status: res.status, data: data };
                } catch(e) {
                    return { error: e.message };
                }
            })()
            """
            res = await call("Runtime.evaluate", {"expression": login_js, "awaitPromise": True, "returnByValue": True})
            print("API Login result:", json.dumps(res.get("result", {}).get("result", {}).get("value"), indent=2))

            # Now navigate to /terminal
            print("Navigating to /terminal with session cookie...")
            await call("Page.navigate", {"url": "https://catrader.site/terminal"})
            await asyncio.sleep(4)

            res = await call("Runtime.evaluate", {"expression": "location.href"})
            curr_url = res.get("result", {}).get("result", {}).get("value")
            print("Current URL after navigating to /terminal:", curr_url)

            # Now collect logs and inspect everything
            exceptions = []
            console_msgs = []
            net_fails = []

            # Listen for 6 seconds while page loads and runs initial API calls
            t0 = time.time()
            while time.time() - t0 < 6:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=0.3)
                    msg = json.loads(raw)
                    method = msg.get("method", "")
                    if "exception" in method.lower():
                        details = msg.get("params", {}).get("exceptionDetails", {})
                        exc_text = details.get("text", "")
                        exc_desc = details.get("exception", {}).get("description", "")
                        line = details.get("lineNumber", 0)
                        exceptions.append(f"Line {line}: {exc_text} - {exc_desc}")
                    elif "console" in method.lower():
                        c_type = msg.get("params", {}).get("type")
                        args = [str(a.get("value", a.get("description", ""))) for a in msg.get("params", {}).get("args", [])]
                        console_msgs.append(f"[{c_type}] " + " ".join(args))
                    elif method == "Network.responseReceived":
                        resp = msg.get("params", {}).get("response", {})
                        status = resp.get("status", 0)
                        url = resp.get("url", "")
                        if status >= 400 and "catrader.site" in url:
                            net_fails.append(f"{status} {url}")
                except asyncio.TimeoutError:
                    pass

            print("\n" + "="*50)
            print("EXCEPTIONS ENCOUNTERED:")
            for e in exceptions:
                print("  ! ", e)
            if not exceptions:
                print("  None.")

            print("\nFAILED NETWORK REQUESTS:")
            for nf in net_fails:
                print("  ! ", nf)
            if not net_fails:
                print("  None.")

            print("\nCONSOLE WARNINGS/ERRORS:")
            for cm in console_msgs:
                if any(k in cm for k in ['[error]', '[warn', 'Error', 'Failed']):
                    print("  ", cm)

            print("\n" + "="*50)
            print("DIAGNOSING USER SPECIFIC ITEMS:")

            # 1. Inspect Candlestick Patterns, Chart Patterns, Trend Pattern in DOM
            patterns_diag = """
            (function() {
                return {
                    patternListHTML: document.getElementById('patternList')?.innerHTML?.slice(0, 300),
                    patternListCount: document.querySelectorAll('#patternList .pattern-card')?.length,
                    patternScanStatus: document.getElementById('patternScanStatus')?.textContent,
                    structureBoxHTML: document.getElementById('structureBox')?.innerHTML?.slice(0, 300),
                    structureStatus: document.getElementById('structureStatus')?.textContent,
                    chartPatternListHTML: document.getElementById('chartPatternList')?.innerHTML?.slice(0, 300),
                    chartPatternListCount: document.querySelectorAll('#chartPatternList .pattern-card')?.length,
                    chartPatternStatus: document.getElementById('chartPatternStatus')?.textContent
                };
            })()
            """
            res = await call("Runtime.evaluate", {"expression": patterns_diag, "returnByValue": True})
            print("1. Patterns DOM State:", json.dumps(res.get("result", {}).get("result", {}).get("value"), indent=2))

            # 2. Inspect Option Search Dropdown
            opt_search_diag = """
            (function() {
                const input = document.getElementById('chartRecoOptionSearch') || document.getElementById('optionSearchBox');
                const menu = document.getElementById('chartRecoOptionSuggestions') || document.getElementById('optionSuggestions');
                return {
                    inputFound: !!input,
                    inputId: input?.id,
                    inputValue: input?.value,
                    menuFound: !!menu,
                    menuId: menu?.id,
                    menuDisplay: menu ? window.getComputedStyle(menu).display : null,
                    menuChildren: menu?.children?.length,
                    menuHTML: menu?.innerHTML?.slice(0, 200)
                };
            })()
            """
            res = await call("Runtime.evaluate", {"expression": opt_search_diag, "returnByValue": True})
            print("\n2. Option Search Dropdown State:", json.dumps(res.get("result", {}).get("result", {}).get("value"), indent=2))

            # Test typing into option search
            test_type_search = """
            (function() {
                const input = document.getElementById('chartRecoOptionSearch') || document.getElementById('optionSearchBox');
                if (input) {
                    input.focus();
                    input.value = 'NIFTY 23500';
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                    return 'TYPED';
                }
                return 'INPUT_NOT_FOUND';
            })()
            """
            await call("Runtime.evaluate", {"expression": test_type_search})
            await asyncio.sleep(1.5)

            res = await call("Runtime.evaluate", {"expression": opt_search_diag, "returnByValue": True})
            print("2b. Option Search after typing 'NIFTY 23500':", json.dumps(res.get("result", {}).get("result", {}).get("value"), indent=2))

            # 3. Recommendation Rationale (All 5 Pointers)
            reco_rationale_diag = """
            (function() {
                return {
                    headerTag: document.getElementById('recoRationaleSignalTag')?.textContent,
                    techCount: document.getElementById('recoTechConfluenceCount')?.textContent,
                    row1_tech: document.getElementById('recoRationaleTechnicals')?.children?.length,
                    row1_tech_html: document.getElementById('recoRationaleTechnicals')?.innerHTML?.slice(0, 200),
                    row2_news: document.getElementById('recoRationaleNews')?.children?.length,
                    row2_news_html: document.getElementById('recoRationaleNews')?.innerHTML?.slice(0, 200),
                    row3_greeks: document.getElementById('recoRationaleGreeks')?.children?.length,
                    row3_greeks_html: document.getElementById('recoRationaleGreeks')?.innerHTML?.slice(0, 200),
                    row4_patterns: document.getElementById('recoRationalePatterns')?.children?.length,
                    row4_patterns_html: document.getElementById('recoRationalePatterns')?.innerHTML?.slice(0, 200),
                    row5_other: document.getElementById('recoRationaleOtherFactors')?.children?.length,
                    row5_other_html: document.getElementById('recoRationaleOtherFactors')?.innerHTML?.slice(0, 200)
                };
            })()
            """
            res = await call("Runtime.evaluate", {"expression": reco_rationale_diag, "returnByValue": True})
            print("\n3. Recommendation Rationale (5 pointers):", json.dumps(res.get("result", {}).get("result", {}).get("value"), indent=2))

            # 4. Check CRUDEOIL Option Chain
            crude_diag = """
            (async function() {
                // Switch symbol or load CRUDEOIL option chain
                try {
                    const res = await fetch('/api/options/CRUDEOIL');
                    const data = await res.json();
                    return {
                        status: res.status,
                        is_mock: data.is_mock || data.mock || false,
                        underlying: data.underlying,
                        atm_strike: data.atm_strike,
                        strikes_count: data.strikes?.length,
                        sample_strike: data.strikes?.[0],
                        expiry: data.expiry,
                        expiries: data.expiries
                    };
                } catch(e) {
                    return { error: e.message };
                }
            })()
            """
            res = await call("Runtime.evaluate", {"expression": crude_diag, "awaitPromise": True, "returnByValue": True})
            print("\n4. CRUDEOIL Option API check from browser:", json.dumps(res.get("result", {}).get("result", {}).get("value"), indent=2))

    asyncio.run(run())
finally:
    proc.terminate()
