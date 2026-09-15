import urllib.request, json, asyncio, websockets, os, subprocess, time

PORT = 9252
chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
proc = subprocess.Popen([
    chrome_path,
    "--headless=new",
    f"--remote-debugging-port={PORT}",
    "--disable-gpu",
    "--no-first-run",
    "--no-default-browser-check",
    "about:blank"
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2)

try:
    with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json/list') as resp:
        targets = json.loads(resp.read().decode())
    page_target = next(t for t in targets if t.get('type') == 'page')
    ws_url = page_target['webSocketDebuggerUrl']

    async def test():
        async with websockets.connect(ws_url) as ws:
            mid = 1
            async def call(method, params=None):
                nonlocal mid
                mid += 1
                cid = mid
                await ws.send(json.dumps({'id': cid, 'method': method, 'params': params or {}}))
                while True:
                    m = await ws.recv()
                    d = json.loads(m)
                    if d.get('id') == cid:
                        return d
            
            async def listen():
                try:
                    while True:
                        m = await ws.recv()
                        d = json.loads(m)
                        if d.get('method') == 'Runtime.exceptionThrown':
                            print('RUNTIME EXCEPTION:', json.dumps(d['params']['exceptionDetails'], indent=2))
                        elif d.get('method') == 'Runtime.consoleAPICalled':
                            typ = d['params']['type']
                            if typ in ['error', 'warning', 'log']:
                                args = [str(a.get('value') or a.get('description')) for a in d['params']['args']]
                                print(f'CONSOLE {typ.upper()}:', ' '.join(args[:4]))
                except asyncio.CancelledError:
                    pass

            await call('Runtime.enable')
            await call('Page.enable')
            
            listener = asyncio.create_task(listen())
            
            p = os.path.abspath("terminal.html").replace("\\", "/")
            url = f"file:///{p}"
            await call('Page.navigate', {'url': url})
            await asyncio.sleep(4)
            listener.cancel()

    asyncio.run(test())
finally:
    proc.terminate()

