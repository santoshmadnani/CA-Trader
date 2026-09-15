import subprocess, time, json, urllib.request, asyncio, websockets, tempfile, re

chrome_path = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
PORT = 9235
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

            # Let's test ranges around 3800-4039
            for k in range(3800, len(lines)-1, 10):
                sub = '\n'.join(lines[1:k]) + '\n})();'
                res = await call('Runtime.compileScript', {'expression': sub, 'sourceURL': 't.js', 'persistScript': False})
                err = res.get('result', {}).get('exceptionDetails')
                if not err:
                    print(f'*** LINES 1 to {k} + closure is VALID! ***')
                else:
                    desc = err.get('exception', {}).get('description', '')
                    line_err = err.get('lineNumber')
                    if 'Unexpected end of input' not in desc:
                        print(f'At k={k}: {desc} at line {line_err}')

    asyncio.run(run())
finally:
    proc.terminate()

