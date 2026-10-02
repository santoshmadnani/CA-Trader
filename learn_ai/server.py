"""
Standalone Learn AI Server
Runs independently on port 5050 to explore and practice CA Trader code.
"""

import http.server
import json
import os
import re
import socketserver
import urllib.parse
from pathlib import Path
import requests

PORT = 5050
BASE_DIR = Path(__file__).resolve().parent
REPO_DIR = BASE_DIR.parent

# Load .env manually if present
env_file = REPO_DIR / ".env"
GEMINI_KEY = ""
if env_file.exists():
    with open(env_file, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.startswith("GEMINI_API_KEY="):
                GEMINI_KEY = line.split("=", 1)[1].strip()

FALLBACK_GLOSSARY = {
    "delta": {
        "term": "Delta (Δ)",
        "plain_summary": "Delta measures how much an option's price moves when the underlying stock moves by ₹1.",
        "real_life_analogy": "Like a car's gas pedal: pressing down determines how fast the speedometer needle moves.",
        "in_ca_trader": "Calculated via Black-Scholes in app.py (line 2941) and displayed in terminal.html (line 20145).",
        "what_if_changed": "A higher Delta (0.80) means your option acts like a stock; a low Delta (0.15) moves slowly."
    },
    "theta": {
        "term": "Theta (Θ)",
        "plain_summary": "Theta is time decay: how much money an option loses each passing day just by sitting in your account.",
        "real_life_analogy": "Like an ice cream cone on a hot afternoon: every minute you hold it, a little bit melts away.",
        "in_ca_trader": "Computed in app.py bs_greeks() and shown in terminal.html Greek simulation modal.",
        "what_if_changed": "Holding the option over the weekend without price movement will cost you money in time decay."
    }
}


class LearnAIHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            index_path = BASE_DIR / "index.html"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            with open(index_path, "rb") as f:
                self.wfile.write(f.read())
            return

        elif path == "/api/learn-ai/directory":
            idx_path = BASE_DIR / "code_index.json"
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            if idx_path.exists():
                with open(idx_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.wfile.write(b"{}")
            return

        elif path == "/api/learn-ai/code-slice":
            qs = urllib.parse.parse_qs(parsed.query)
            file_param = qs.get("file", ["terminal.html"])[0]
            start = int(qs.get("start", [1])[0])
            end = int(qs.get("end", [50])[0])

            target = REPO_DIR / ("app.py" if "app" in file_param.lower() else "terminal.html")
            lines_out = []
            if target.exists():
                with open(target, "r", encoding="utf-8", errors="replace") as f:
                    for i, line in enumerate(f, start=1):
                        if i >= start and i <= end:
                            lines_out.append({"line_num": i, "content": line.rstrip("\r\n")})
                        elif i > end:
                            break

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "file": target.name, "start": start, "end": end, "total_fetched": len(lines_out), "lines": lines_out}).encode("utf-8"))
            return

        return super().do_GET()

    def do_POST(self):
        if self.path == "/api/learn-ai/explain":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body.decode("utf-8"))
            except Exception:
                data = {}

            term = data.get("term", "").strip()
            context = data.get("context", "").strip()

            result = None
            if GEMINI_KEY and term:
                prompt = (
                    f"Explain this trading/code term to a complete beginner in simple layman words with a real-life analogy:\n"
                    f"Term: {term}\nContext: {context}\n"
                    f"Format strictly in JSON: {{\"term\": \"{term}\", \"plain_summary\": \"...\", \"real_life_analogy\": \"...\", \"in_ca_trader\": \"...\", \"what_if_changed\": \"...\"}}"
                )
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={GEMINI_KEY}"
                try:
                    r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=8)
                    if r.status_code == 200:
                        txt = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                        m = re.search(r"\{.*\}", txt, re.DOTALL)
                        if m:
                            result = json.loads(m.group(0))
                            result["ok"] = True
                            result["source"] = "gemini-3.8-flash"
                except Exception:
                    pass

            if not result:
                clean = term.lower().replace(" ", "_")
                fb = FALLBACK_GLOSSARY.get(clean, {
                    "term": term,
                    "plain_summary": f"'{term}' is a key trading calculation or UI setting in the terminal.",
                    "real_life_analogy": "Like a dial on a car dashboard: each part measures one specific aspect of the drive.",
                    "in_ca_trader": "Found inside app.py or terminal.html.",
                    "what_if_changed": "Modifying it changes the numbers displayed on screen or how signals trigger."
                })
                result = {"ok": True, "source": "local_mentor_glossary", **fb}

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()


if __name__ == "__main__":
    os.chdir(str(BASE_DIR))
    print(f"==================================================")
    print(f"  CA TRADER — LEARN AI DEDICATED APP SERVER")
    print(f"  Open in your browser: http://localhost:{PORT}")
    print(f"==================================================")
    with socketserver.TCPServer(("", PORT), LearnAIHandler) as httpd:
        httpd.serve_forever()
