import asyncio, websockets, json, subprocess, urllib.request, time

PORT = 9264
proc = subprocess.Popen([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new', f'--remote-debugging-port={PORT}', '--disable-gpu', 'about:blank'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2)
try:
    with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json/list') as resp:
        targets = json.loads(resp.read().decode())
    page_target = next(t for t in targets if t.get('type') == 'page')
    ws_url = page_target['webSocketDebuggerUrl']

    async def verify_panels():
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
            
            tabs_to_test = ['charts', 'options', 'news', 'reco', 'fundamentals', 'movers', 'other-factors', 'orders', 'funds', 'console', 'reports', 'quiz']
            results = {}
            for t in tabs_to_test:
                eval_js = f"""(async () => {{
                    if(typeof window.showTab === 'function') window.showTab('{t}');
                    await new Promise(r => setTimeout(r, 700));
                    const p = document.getElementById('panel-{t}');
                    return {{
                        found: !!p,
                        hasActiveClass: p ? p.classList.contains('active') : false,
                        textLength: p ? p.innerText.trim().length : 0,
                        snippet: p ? p.innerText.trim().slice(0, 100).replace(/\\s+/g, ' ') : ''
                    }};
                }})()"""
                res = await call('Runtime.evaluate', {'expression': eval_js, 'awaitPromise': True, 'returnByValue': True})
                results[t] = res.get('result', {}).get('result', {}).get('value')
            
            print(json.dumps(results, indent=2))

    asyncio.run(verify_panels())
finally:
    proc.terminate()

