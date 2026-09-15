import subprocess, time, json, urllib.request, asyncio, websockets, tempfile, re

chrome_path = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
PORT = 9251
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

            # We replace await in lines 4020..4038 with void
            clean_lines = [l.replace('await loadProfile()', 'loadProfile()').replace('await W0()', 'W0()') for l in lines]
            
            # Let's test lines 1..k wrapped in async function
            # Binary search for the line that introduces a syntax error
            low = 5
            high = 4038
            while low < high:
                mid_line = (low + high) // 2
                code = 'async function __OUTER__() {\n' + '\n'.join(clean_lines[2:mid_line]) + '\n}'
                res = await call('Runtime.compileScript', {'expression': code, 'sourceURL': 't.js', 'persistScript': False})
                err = res.get('result', {}).get('exceptionDetails')
                desc = err.get('exception', {}).get('description', '') if err else ''
                if err and 'Unexpected end of input' not in desc:
                    high = mid_line
                else:
                    low = mid_line + 1

            print(f'*** First line that breaks __OUTER__: {low} ***')
            for i in range(max(0, low-3), min(len(lines), low+4)):
                print(f'{i}: {lines[i]}')
            
            # Print the exact error for low
            code = 'async function __OUTER__() {\n' + '\n'.join(clean_lines[2:low]) + '\n}'
            res = await call('Runtime.compileScript', {'expression': code, 'sourceURL': 't.js', 'persistScript': False})
            print('Error details:', res.get('result', {}).get('exceptionDetails'))

    asyncio.run(run())
finally:
    proc.terminate()
