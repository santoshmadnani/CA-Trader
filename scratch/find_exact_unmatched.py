import subprocess, time, json, urllib.request, asyncio, websockets, tempfile, re

chrome_path = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
PORT = 9249
proc = subprocess.Popen([chrome_path, '--headless=new', f'--user-data-dir={tempfile.mkdtemp()}', f'--remote-debugging-port={PORT}', '--disable-gpu', 'about:blank'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2)

try:
    with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json/list') as resp:
        targets = json.loads(resp.read().decode())
    ws_url = next(t for t in targets if t.get('type') == 'page')['webSocketDebuggerUrl']

    with open('terminal.html', 'r', encoding='utf-8') as f:
        html = f.read()

    scripts = [m.group(1) for m in re.finditer(r'<script\b[^>]*>(.*?)</script>', html, re.DOTALL)]
    sc2 = scripts[2]
    lines = sc2.split('\n')

    async def run():
        async with websockets.connect(ws_url) as ws:
            mid = 1
            async def call(method, params=None):
                nonlocal mid; mid += 1; cur_id = mid
                await ws.send(json.dumps({'id': cur_id, 'method': method, 'params': params or {}}))
                while True:
                    m = await ws.recv()
                    d = json.loads(m)
                    if d.get('id') == cur_id: return d

            await call('Runtime.enable')

            for k in range(2, 578):
                code = '\n'.join(lines[1:k]) + '\n})();'
                res = await call('Runtime.compileScript', {'expression': code, 'sourceURL': 't.js', 'persistScript': False})
                err = res.get('result', {}).get('exceptionDetails')
                if err:
                    desc = err.get('exception', {}).get('description', '')
                    if "Unexpected token ')'" in desc:
                        print(f"*** Unexpected token ) at k={k}! Line {k-1}: {lines[k-1]} ***")
                        break

    asyncio.run(run())
finally:
    proc.terminate()
