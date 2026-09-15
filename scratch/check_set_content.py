import subprocess, time, json, urllib.request, asyncio, websockets, os

PORT_CHROME = 9288
chrome_path = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
proc = subprocess.Popen([
    chrome_path,
    '--headless=new',
    f'--remote-debugging-port={PORT_CHROME}',
    '--disable-gpu',
    'about:blank'
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

for _ in range(10):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{PORT_CHROME}/json/list') as resp:
            targets = json.loads(resp.read().decode())
            break
    except Exception:
        time.sleep(0.5)

ws_url = targets[0]['webSocketDebuggerUrl']

try:
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

            with open('terminal.html', 'r', encoding='utf-8') as f:
                html = f.read()

            frame_tree = await call('Page.getFrameTree')
            main_frame_id = frame_tree['result']['frameTree']['frame']['id']
            print('Setting document content...')
            await call('Page.setDocumentContent', {'frameId': main_frame_id, 'html': html})
            await asyncio.sleep(4)

            expr = "JSON.stringify({title: document.title, S: window.CATraderSymbol, onSym: typeof window.onSymbolChanged, W0: typeof window.W0, wl_count: document.querySelectorAll('.wl-item').length, chartSym: document.getElementById('chartSymbolTitle')?.textContent})"
            res = await call('Runtime.evaluate', {
                'expression': expr,
                'returnByValue': True
            })
            print('SET_CONTENT RESULT:', res.get('result', {}).get('result', {}).get('value'))

    asyncio.run(run())
finally:
    proc.terminate()

