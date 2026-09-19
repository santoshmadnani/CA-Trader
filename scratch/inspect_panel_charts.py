with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()
import subprocess, time, json, urllib.request, asyncio, websockets, ssl, sys, os
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import re
# find start of panel-charts
p_start = text.find('id="panel-charts"')
p_end = text.find('id="panel-', p_start + 20)
print("panel-charts length:", p_end - p_start)
charts_content = text[p_start:p_end]
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 9301

for m in re.finditer(r'<div[^>]+id=["\']([^"\']+)["\'][^>]*>', charts_content):
    elem_id = m.group(1)
    if any(k in elem_id.lower() for k in ['summary', 'tech', 'pattern', 'factor', 'news', 'reco', 'greek', 'opt']):
        print("Elem in panel-charts:", elem_id)
proc = subprocess.Popen([
    CHROME,
    "--headless=new",
    f"--remote-debugging-port={PORT}",
    "--disable-gpu",
    "--no-first-run",
    "--no-default-browser-check",
    "about:blank"
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

card_titles = re.findall(r'class=["\'](?:card-title|section-title)[^"\']*["\'][^>]*>([^<]+)<', charts_content)
print("Card/section titles in panel-charts:", card_titles[:15])
time.sleep(2)

async def main():
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list") as resp:
            targets = json.loads(resp.read().decode())
        page_target = next(t for t in targets if t.get("type") == "page")
        ws_url = page_target["webSocketDebuggerUrl"]

        async with websockets.connect(ws_url) as ws:
            mid = 0
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

            async def eval_js(expr):
                r = await call("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
                return r.get("result", {}).get("result", {}).get("value")

            await call("Runtime.enable")
            await call("Page.enable")

            # Login
            await call("Page.navigate", {"url": "https://catrader.site/login"})
            await asyncio.sleep(2)
            await eval_js("""
            (() => {
                const e = document.querySelector('input[type="email"], #e, input[name="email"]');
                const p = document.querySelector('input[type="password"], #p, input[name="password"]');
                const btn = document.querySelector('button[type="submit"], #f button, .btn-primary') || document.querySelector('button');
                if (e && p && btn) {
                    e.value = 'santoshmadnani@catrader.site';
                    p.value = 'Santosh@9340925132#';
                    e.dispatchEvent(new Event('input', { bubbles: true }));
                    p.dispatchEvent(new Event('input', { bubbles: true }));
                    btn.click();
                }
            })()
            """)
            await asyncio.sleep(3)

            # Navigate to terminal
            await call("Page.navigate", {"url": "https://catrader.site/terminal"})
            await asyncio.sleep(5)

            # Click Charts tab
            await eval_js("document.querySelector('.navtab[data-tab=\"charts\"]')?.click()")
            await asyncio.sleep(1)

            # Detailed inspection of panel-charts and its parents
            inspect = await eval_js("""
            (() => {
                const p = document.getElementById('panel-charts');
                if (!p) return 'NO panel-charts';
                
                let cur = p;
                const ancestors = [];
                while(cur && cur !== document.body) {
                    const cs = window.getComputedStyle(cur);
                    ancestors.push({
                        tag: cur.tagName,
                        id: cur.id,
                        className: cur.className,
                        display: cs.display,
                        height: cur.offsetHeight,
                        width: cur.offsetWidth,
                        overflow: cs.overflow,
                        position: cs.position,
                        visibility: cs.visibility
                    });
                    cur = cur.parentElement;
                }
                
                const children = Array.from(p.children).map(c => {
                    const cs = window.getComputedStyle(c);
                    return {
                        tag: c.tagName,
                        id: c.id,
                        className: c.className,
                        display: cs.display,
                        height: c.offsetHeight,
                        width: c.offsetWidth,
                        visibility: cs.visibility
                    };
                });

                return {
                    ancestors,
                    childrenCount: p.children.length,
                    children,
                    innerHTMLSnippet: p.innerHTML.substring(0, 300)
                };
            })()
            """)
            print("Inspection:", json.dumps(inspect, indent=2))

    finally:
        proc.kill()

asyncio.run(main())
