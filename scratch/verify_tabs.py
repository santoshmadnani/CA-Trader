import asyncio, websockets, json, subprocess, urllib.request, time

PORT = 9266
proc = subprocess.Popen([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new', f'--remote-debugging-port={PORT}', '--disable-gpu', 'about:blank'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2)
try:
    with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json/list') as resp:
        targets = json.loads(resp.read().decode())
    page_target = next(t for t in targets if t.get('type') == 'page')
    ws_url = page_target['webSocketDebuggerUrl']

    async def verify_all():
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
            await asyncio.sleep(5)
            
            tabs = ['charts', 'options', 'news', 'reco', 'fundamentals', 'funds', 'auto', 'backtest']
            tab_results = {}
            for t in tabs:
                eval_js = f"""(async () => {{
                    const btn = document.querySelector('.navtab[data-tab="{t}"]');
                    if(btn) btn.click();
                    await new Promise(r => setTimeout(r, 600));
                    const pane = document.getElementById('{t}Tab') || document.querySelector('.tab-pane.active');
                    return {{
                        found: !!pane,
                        textLength: pane ? pane.innerText.trim().length : 0,
                        snippet: pane ? pane.innerText.trim().slice(0, 80).replace(/\\s+/g, ' ') : ''
                    }};
                }})()"""
                res = await call('Runtime.evaluate', {'expression': eval_js, 'awaitPromise': True, 'returnByValue': True})
                tab_results[t] = res.get('result', {}).get('result', {}).get('value')
            
            print(json.dumps(tab_results, indent=2))

    asyncio.run(verify_all())
finally:
    proc.terminate()

