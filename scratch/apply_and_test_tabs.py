import subprocess
import time
import json
import urllib.request
import asyncio
import websockets
import os

# First, apply the fix to terminal.html
with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

# Verify the exact lines before removing
assert 'gap:8px;position:relative;' in lines[2042], f"Line 2043 mismatch: {lines[2042]}"
assert '</div>' in lines[3043], f"Line 3044 mismatch: {lines[3043]}"

fixed_lines = [l for i, l in enumerate(lines) if i not in (2042, 3043)]

with open('terminal.html', 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print("Applied fix to terminal.html. Now testing with Chrome...")

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT_CHROME = 9233

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

            test_tabs = [
                'charts',
                'options',
                'reco',
                'news',
                'fundamentals',
                'movers',
                'other-factors',
                'orders',
                'funds',
                'console',
                'reports',
                'quiz',
                'tutorial'
            ]
            
            print("\n=== TESTING TAB CLICKS ===")
            all_passed = True
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
                            tab: '{tname}',
                            tabActive: tabEl.classList.contains('active'),
                            panelActive: panel.classList.contains('active'),
                            display: style.display,
                            height: panel.offsetHeight,
                            parentTag: panel.parentElement.tagName,
                            parentClass: panel.parentElement.className
                        }};
                    }})()""",
                    "returnByValue": True
                })
                val = res.get("result", {}).get("result", {}).get("value")
                print(f"Tab '{tname}':", val)
                if not isinstance(val, dict) or not val.get('panelActive') or val.get('height', 0) <= 0:
                    all_passed = False
            
            print(f"\nALL TABS PASSED AND VISIBLE: {all_passed}")

    asyncio.run(run())
finally:
    proc.terminate()

