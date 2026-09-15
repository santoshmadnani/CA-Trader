with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()
import asyncio, websockets, json, subprocess, urllib.request, time

print("Length of terminal.html:", len(content))
PORT = 9265
proc = subprocess.Popen([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new', f'--remote-debugging-port={PORT}', '--disable-gpu', 'about:blank'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2)
try:
    with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json/list') as resp:
        targets = json.loads(resp.read().decode())
    page_target = next(t for t in targets if t.get('type') == 'page')
    ws_url = page_target['webSocketDebuggerUrl']

# Look for tabs, panels, sections
import re
panels = re.findall(r'id=["\'](panel-[^"\']+)["\']', content)
print("Panels found:", panels)
    async def verify_sections():
        async with websockets.connect(ws_url) as ws:
            mid = 1
            async def call(method, params=None):
                nonlocal mid
                mid += 1
                cid = mid
                await ws.send(json.dumps({'id': cid, 'method': method, 'params': params or {}}))
                while True:
                    d = json.loads(await ws.recv())
                    if d.get('id') == cid:
                        return d
            
            await call('Runtime.enable')
            await call('Page.navigate', {'url': 'https://catrader.site/login'})
            await asyncio.sleep(2)
            await call('Runtime.evaluate', {'expression': '''fetch('/api/auth/login', {method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:'santoshmadnani@catrader.site',password:'Trader@123'})})''', 'awaitPromise': True})
            
            await call('Page.navigate', {'url': 'https://catrader.site/terminal'})
            await asyncio.sleep(6)
            
            navtabs_js = """Array.from(document.querySelectorAll('.navtab')).map(t => ({
                id: t.id,
                tab: t.dataset.tab,
                text: t.innerText.trim(),
                active: t.classList.contains('active')
            }))"""
            res_tabs = await call('Runtime.evaluate', {'expression': navtabs_js, 'returnByValue': True})
            print('Navtabs:', json.dumps(res_tabs.get('result', {}).get('result', {}).get('value'), indent=2))

navtabs = re.findall(r'class=["\'][^"\']*navtab[^"\']*["\'][^>]*', content)
print(f"Navtab elements found ({len(navtabs)}):")
for nt in navtabs[:10]:
    print("  ", nt[:100])
            sections_js = """Array.from(document.querySelectorAll('.tab-content, .tab-pane, [data-tab-content], section')).filter(el => el.id).map(el => ({
                id: el.id,
                display: window.getComputedStyle(el).display,
                visibility: window.getComputedStyle(el).visibility,
                textLen: el.innerText.trim().length,
                snippet: el.innerText.trim().slice(0, 60).replace(/\\s+/g, ' ')
            }))"""
            res_sections = await call('Runtime.evaluate', {'expression': sections_js, 'returnByValue': True})
            print('Sections:', json.dumps(res_sections.get('result', {}).get('result', {}).get('value'), indent=2))

tab_listeners = [i for i, line in enumerate(content.splitlines()) if 'loadtabdata' in line.lower() or 'showtab' in line.lower()]
print(f"Lines referencing showTab/loadTabData ({len(tab_listeners)}):", tab_listeners[:20])

    asyncio.run(verify_sections())
finally:
    proc.terminate()
