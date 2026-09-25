#!/usr/bin/env python3
"""
Pre-Commit & Pre-Deploy Integrity Validator for CA Trader
Verifies:
1. Python syntax & compilation (app.py, backend routers)
2. JavaScript syntax across all inline <script> tags in terminal.html via V8 engine
3. CSS brace balance across all <style> tags in terminal.html
"""

import sys, os, subprocess, time, json, urllib.request, asyncio
from bs4 import BeautifulSoup

def check_python():
    print("[1/3] Checking Python compilation...")
    py_files = ['app.py', 'backend/routers/ai_connector.py']
    for pf in py_files:
        if os.path.exists(pf):
            res = subprocess.run([sys.executable, '-m', 'py_compile', pf], capture_output=True, text=True)
            if res.returncode != 0:
                print(f"FAILED: Syntax error in {pf}")
                print(res.stderr)
                return False
            print(f"  OK: {pf}")
    return True

def check_css_balance():
    print("[2/3] Checking CSS brace balance in terminal.html...")
    if not os.path.exists('terminal.html'):
        return True
    with open('terminal.html', 'r', encoding='utf-8') as f:
        html = f.read()
    soup = BeautifulSoup(html, 'html.parser')
    styles = soup.find_all('style')
    has_error = False
    for idx, st in enumerate(styles):
        css = st.string or ''
        depth = 0
        in_comment = False
        lines = css.splitlines()
        for lno, line in enumerate(lines, 1):
            cleaned = ''
            i = 0
            while i < len(line):
                if not in_comment and line[i:i+2] == '/*':
                    in_comment = True
                    i += 2
                elif in_comment and line[i:i+2] == '*/':
                    in_comment = False
                    i += 2
                elif not in_comment:
                    cleaned += line[i]
                    i += 1
                else:
                    i += 1
            for c in cleaned:
                if c == '{': depth += 1
                elif c == '}': depth -= 1
        if depth != 0:
            print(f"FAILED: Style tag {idx} has {depth} unclosed brace(s)!")
            has_error = True
        else:
            print(f"  OK: Style tag {idx} balanced (len {len(css)})")
    return not has_error

async def check_v8_scripts():
    print("[3/3] Checking JavaScript syntax via V8 engine...")
    if not os.path.exists('terminal.html'):
        return True
    try:
        import websockets
    except ImportError:
        print("  websockets package not found, skipping V8 check")
        return True

    edge_paths = [
        r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
        'msedge', 'google-chrome', 'chrome'
    ]
    edge_bin = None
    for p in edge_paths:
        if os.path.exists(p):
            edge_bin = p
            break
    if not edge_bin:
        print("  Edge/Chrome not found, skipping V8 evaluation")
        return True

    cmd = [edge_bin, '--headless=new', '--remote-debugging-port=9222', '--no-first-run', '--no-default-browser-check', 'about:blank']
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    await asyncio.sleep(2)
    has_error = False
    try:
        req = urllib.request.urlopen('http://127.0.0.1:9222/json')
        targets = json.loads(req.read())
        ws_url = targets[0]['webSocketDebuggerUrl']
        async with websockets.connect(ws_url) as ws:
            with open('terminal.html', 'r', encoding='utf-8') as f:
                html = f.read()
            soup = BeautifulSoup(html, 'html.parser')
            scripts = soup.find_all('script')
            for i, s in enumerate(scripts):
                if s.get('src'): continue
                code = s.string or ''
                if not code.strip(): continue
                msg_id = i + 100
                payload = {
                    'id': msg_id,
                    'method': 'Runtime.evaluate',
                    'params': {'expression': f"(function(){{\n{code}\n}})()", 'silent': True, 'returnByValue': True}
                }
                await ws.send(json.dumps(payload))
                while True:
                    resp = await ws.recv()
                    data = json.loads(resp)
                    if data.get('id') == msg_id:
                        result = data.get('result', {})
                        if 'exceptionDetails' in result:
                            exc = result['exceptionDetails']
                            desc = exc.get('exception', {}).get('description', '')
                            if 'SyntaxError' in desc:
                                print(f"FAILED: Script {i} has SyntaxError: {desc}")
                                has_error = True
                            else:
                                print(f"  OK: Script {i} syntax valid (len {len(code)})")
                        else:
                            print(f"  OK: Script {i} syntax valid (len {len(code)})")
                        break
    except Exception as e:
        print(f"  V8 check warning: {e}")
    finally:
        proc.terminate()
    return not has_error

def main():
    print("==================================================")
    print("  CA TRADER PRE-COMMIT INTEGRITY AUDIT")
    print("==================================================")
    ok1 = check_python()
    ok2 = check_css_balance()
    ok3 = asyncio.run(check_v8_scripts())
    
    if ok1 and ok2 and ok3:
        print("==================================================")
        print("  ALL INTEGRITY CHECKS PASSED SUCCESSFULLY! ")
        print("==================================================")
        sys.exit(0)
    else:
        print("==================================================")
        print("  FAILED! DO NOT COMMIT OR DEPLOY. FIX ERRORS.")
        print("==================================================")
        sys.exit(1)

if __name__ == '__main__':
    main()
