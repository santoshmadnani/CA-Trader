import subprocess
import re

def stop_server(port=8000):
    print("=" * 60)
    print("       STOPPING CA TRADER LAPTOP SERVER & TUNNEL")
    print("=" * 60)

    # 1. Kill any process listening on port 8000
    try:
        out = subprocess.check_output(f'netstat -ano | findstr :{port}', shell=True, text=True)
        pids = set()
        for line in out.splitlines():
            line = line.strip()
            if f":{port}" in line and "LISTENING" in line:
                parts = line.split()
                if parts:
                    pid = parts[-1]
                    if pid.isdigit() and pid != "0":
                        pids.add(pid)
        for pid in pids:
            print(f"[STOP] Stopping backend server (PID: {pid})...")
            subprocess.run(f"taskkill /F /PID {pid} /T", shell=True, capture_output=True)
    except subprocess.CalledProcessError:
        print(f"[INFO] No process listening on port {port}.")

    # 2. Kill cloudflared process
    try:
        out = subprocess.check_output('tasklist /FI "IMAGENAME eq cloudflared.exe"', shell=True, text=True)
        if "cloudflared.exe" in out.lower():
            print("[STOP] Stopping Cloudflare Tunnel (cloudflared.exe)...")
            subprocess.run("taskkill /F /IM cloudflared.exe /T", shell=True, capture_output=True)
        else:
            print("[INFO] Cloudflare tunnel is not running.")
    except Exception:
        pass

    print("\n[SUCCESS] Server and tunnel stop complete.")

if __name__ == "__main__":
    stop_server(8000)
