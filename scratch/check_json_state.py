import subprocess, time, json, urllib.request, asyncio, websockets, tempfile, os

PORT = 9245
chrome_path = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
temp_dir = tempfile.mkdtemp()

proc = subprocess.Popen([
    chrome_path,
    '--headless=new',
    f'--user-data-dir={temp_dir}',
    f'--remote-debugging-port={PORT}',
    '--disable-gpu',
    '--no-first-run',
    '--no-default-browser-check',
    'about:blank'
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2)

try:
    with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json/list') as resp:
        targets = json.loads(resp.read().decode())
    ws_url = targets[0]['webSocketDebuggerUrl']

    async def run():
        async with websockets.connect(ws_url) as ws:
            mid = 1
            async def call(method, params=None):
                nonlocal mid
                mid += 1
                cur_id = mid
                await ws.send(json.dumps({'id': cur_id, 'method': method, 'params': params or {}}))
                while True:
                    d = json.loads(await ws.recv())
                    if d.get('id') == cur_id:
                        return d

            await call('Runtime.enable')
            await call('Page.enable')

            p = os.path.abspath('terminal.html').replace('\\', '/')
            await call('Page.navigate', {'url': f'file:///{p}'})
            await asyncio.sleep(4)

            expr = "JSON.stringify({A: typeof window.A, state: typeof window.state, onSymbolChanged: typeof window.onSymbolChanged, W0: typeof window.W0, wl_length: document.getElementById('wl-list')?.children?.length, symbol: window.CATraderSymbol})"
            res = await call('Runtime.evaluate', {
                'expression': expr,
                'returnByValue': True
            })
            print('RESULT:', res.get('result', {}).get('result', {}).get('value'))

    asyncio.run(run())
finally:
    proc.terminate()

