import urllib.request, ssl, re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request('https://catrader.site/terminal', headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
        html = r.read().decode('utf-8', errors='replace')
        print(f"Terminal HTML size: {len(html)} chars")
        scripts = re.findall(r'<script[^>]*src=["\']([^"\']+)["\']', html)
        print("Scripts referenced in HTML:")
        for s in scripts:
            s_url = s if s.startswith('http') else f"https://catrader.site{s}"
            try:
                with urllib.request.urlopen(s_url, timeout=5, context=ctx) as sr:
                    content = sr.read()
                    print(f"  OK {sr.status} ({len(content)} bytes): {s}")
            except Exception as se:
                print(f"  FAILED: {s} -> {se}")

        inline_scripts = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', html, re.DOTALL)
        print(f"Number of inline script tags: {len(inline_scripts)}")
        for idx, scr in enumerate(inline_scripts):
            print(f"  Inline script {idx}: {len(scr)} chars, preview: {scr[:80].strip()!r}")
except Exception as e:
    print('Error:', e)

