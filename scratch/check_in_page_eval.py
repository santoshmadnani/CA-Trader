import http.server, socketserver, threading, subprocess, time, json, urllib.request, asyncio, websockets, tempfile, os

PORT_HTTP = 8795
PORT_CHROME = 9265
DOC_ROOT = r"c:\Users\SantoshMadnani\Documents\CA_Trader\7"

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DOC_ROOT, **kwargs)
    def log_message(self, format, *args):
        pass

httpd = socketserver.TCPServer(('127.0.0.1', PORT_HTTP), Handler)
t = threading.Thread(target=httpd.serve_forever, daemon=True)
t.start()

chrome_path = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
temp_dir = tempfile.mkdtemp()
proc = subprocess.Popen([
    chrome_path,
    '--headless=new',
    f'--user-data-dir={temp_dir}',
    f'--remote-debugging-port={PORT_CHROME}',
    '--disable-gpu',
    'about:blank'
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2)

try:
    with urllib.request.urlopen(f'http://127.0.0.1:{PORT_CHROME}/json/list') as resp:
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

            async def listen():
                try:
                    while True:
                        msg = json.loads(await ws.recv())
                        method = msg.get("method", "")
                        if "exception" in method.lower():
                            details = msg.get("params", {}).get("exceptionDetails", {})
                            print(">>> RUNTIME EXCEPTION:", details.get("text"), details.get("exception", {}).get("description"), "line:", details.get("lineNumber"))
                        elif "console" in method.lower():
                            args = [str(a.get("value", a.get("description", ""))) for a in msg.get("params", {}).get("args", [])]
                            if msg.get("params", {}).get("type") in ["error", "warning"]:
                                print("CONSOLE:", msg.get("params", {}).get("type"), " ".join(args[:4]))
                except asyncio.CancelledError:
                    pass

            await call('Runtime.enable')
            await call('Page.enable')

            listener = asyncio.create_task(listen())

            url = f'http://127.0.0.1:{PORT_HTTP}/terminal.html'
            nav_res = await call('Page.navigate', {'url': url})
            print('Page.navigate result:', nav_res)
            await asyncio.sleep(4)
            listener.cancel()

            res = await call('Runtime.evaluate', {
                'expression': 'Array.from(document.querySelectorAll("script")).map((s, idx) => ({idx: idx, len: s.text.length}))',
                'returnByValue': True
            })
            print('SCRIPTS IN PAGE:', res.get('result', {}).get('result', {}).get('value'))

            expr = "JSON.stringify({title: document.title, A: typeof window.A, state: typeof window.state, onSymbolChanged: typeof window.onSymbolChanged, W0: typeof window.W0, wl_items: document.querySelectorAll('.wl-item').length, chartSym: document.getElementById('chartSymbolTitle')?.textContent, selectedSym: window.CATraderSymbol})"
            res2 = await call('Runtime.evaluate', {
                'expression': expr,
                'returnByValue': True
            })
            print('APP STATE IN HTTP PAGE:', res2.get('result', {}).get('result', {}).get('value'))

    asyncio.run(run())
finally:
    proc.terminate()
    httpd.shutdown()

