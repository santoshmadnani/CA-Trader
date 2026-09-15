import subprocess, time, json, urllib.request, asyncio, websockets, tempfile

PORT = 9270
chrome_path = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
temp_dir = tempfile.mkdtemp()

proc = subprocess.Popen([
    chrome_path, '--headless=new', f'--user-data-dir={temp_dir}', f'--remote-debugging-port={PORT}',
    '--disable-gpu', '--no-first-run', '--no-default-browser-check', 'about:blank'
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2)

try:
    with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json/list') as resp:
        targets = json.loads(resp.read().decode())
    ws_url = next(t for t in targets if t.get('type') == 'page')['webSocketDebuggerUrl']

    async def run():
        async with websockets.connect(ws_url) as ws:
            mid = 1
            async def call(method, params=None):
                nonlocal mid; mid += 1; cur_id = mid
                await ws.send(json.dumps({'id': cur_id, 'method': method, 'params': params or {}}))
                while True:
                    d = json.loads(await ws.recv())
                    if d.get('id') == cur_id: return d

            await call('Page.enable')
            await call('Runtime.enable')

            with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            await call('Page.setDocumentContent', {
                'frameId': (await call('Page.getFrameTree'))['result']['frameTree']['frame']['id'],
                'html': content
            })
            await asyncio.sleep(2)

            for t in ['dashboard', 'charts', 'options', 'news', 'fundamentals', 'movers', 'other-factors', 'orders', 'funds']:
                res = await call('Runtime.evaluate', {
                    'expression': f'(() => {{ showTab("{t}"); const p = document.getElementById("panel-{t}"); return p ? (p.classList.contains("active") ? "ACTIVE, h=" + p.offsetHeight : "NOT ACTIVE") : "NOT FOUND"; }})()'
                })
                print(f'Tab {t}:', res.get('result',{}).get('result',{}).get('value'))

    asyncio.run(run())
finally:
    proc.terminate()

