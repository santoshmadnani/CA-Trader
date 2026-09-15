import subprocess, time, json, urllib.request, asyncio, websockets, tempfile, re

chrome_path = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
PORT = 9245
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

            # Binary search for the line where adding `\n})();` starts failing with "Unexpected token ')'"
            low = 2
            high = 4038
            
            async def test_k(k):
                # We test if lines[1:k+1] followed by `\n})();` is valid or unexpected token ')'
                code = '\n'.join(lines[1:k+1]) + '\n})();'
                res = await call('Runtime.compileScript', {'expression': code, 'sourceURL': 't.js', 'persistScript': False})
                err = res.get('result', {}).get('exceptionDetails')
                if not err:
                    return 'VALID'
                desc = err.get('exception', {}).get('description', '')
                return desc

            # Binary search
            while low < high:
                mid_line = (low + high) // 2
                res_desc = await test_k(mid_line)
                if "Unexpected token ')'" in res_desc:
                    # Too far, the extra brace is at or before mid_line
                    high = mid_line
                else:
                    # Not yet closed or unexpected end of input
                    low = mid_line + 1

            print(f'*** Bisection found critical line: {low} ***')
            for i in range(max(0, low - 5), min(len(lines), low + 6)):
                print(f'{i}: {lines[i]}')

    asyncio.run(run())
finally:
    proc.terminate()

