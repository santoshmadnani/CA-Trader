import urllib.request
import ssl
import socket
import subprocess

def is_port_in_use(port=8000):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex(('127.0.0.1', port)) == 0

def is_process_running(proc_name):
    try:
        out = subprocess.check_output(f'tasklist /FI "IMAGENAME eq {proc_name}"', shell=True, text=True)
        return proc_name.lower() in out.lower()
    except Exception:
        return False

def check_status():
    print("=" * 62)
    print("           CA TRADER - SERVER STATUS INSPECTOR")
    print("=" * 62)
    
    # 1. Local backend on port 8000
    local_ok = is_port_in_use(8000)

    # 2. Cloudflare tunnel process
    tunnel_proc = is_process_running("cloudflared.exe")

    # 3. Public HTTPS check
    public_ok = False
    status_detail = ""
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request("https://catrader.site/health", headers={"User-Agent": "StatusChecker/1.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=6) as resp:
            if resp.status == 200:
                public_ok = True
                status_detail = "200 OK"
    except Exception as e:
        status_detail = str(e)

    # Display results
    print(f"  [1] Local Server (Port 8000):     {'RUNNING' if local_ok else 'STOPPED'}")
    print(f"  [2] Cloudflare Tunnel:             {'CONNECTED' if tunnel_proc else 'STOPPED'}")
    print(f"  [3] Public HTTPS (catrader.site):   {'ONLINE (' + status_detail + ')' if public_ok else 'OFFLINE (' + status_detail + ')'}")
    print(f"  [1] Public HTTPS (catrader.site):   {'ONLINE (' + status_detail + ')' if public_ok else 'OFFLINE (' + status_detail + ')'}")
    print(f"  [2] Oracle Cloud 24/7 Server:      {'ACTIVE & SERVING' if public_ok and not local_ok else ('ACTIVE' if public_ok else 'UNKNOWN')}")
    print(f"  [3] Local Laptop Backend:          {'RUNNING' if local_ok else 'OFFLINE (Cloud is Primary)'}")
    print("=" * 62)
    
    if local_ok and tunnel_proc and public_ok:
    if public_ok:
        print("  >>> ALL SYSTEMS ONLINE! <<<")
        print("  Your server is active and accessible at:")
        print("  Your 24/7 server is active and accessible worldwide at:")
        print("  --> https://catrader.site")
    elif local_ok and not tunnel_proc:
        print("  >>> STATUS: LOCAL ONLY (Cloudflare Tunnel not running) <<<")
        if not local_ok:
            print("  (Running in the cloud - your laptop does NOT need to stay on!)")
    else:
        print("  >>> STATUS: SERVER IS OFFLINE <<<")
        print("  Double-click 'Start CA Trader Server' on your Desktop to start.")
        print("  Use 'Deploy to Oracle Cloud' or 'Start CA Trader Server (Laptop)'.")
    print("=" * 62)

if __name__ == "__main__":
    check_status()

