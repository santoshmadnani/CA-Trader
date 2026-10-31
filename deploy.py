#!/usr/bin/env python3
"""CA Trader: one script to keep GitHub, this folder and the server in sync.

    python deploy.py status         what is where: git state, which server catrader.site points to, server disk use
    python deploy.py sync           copy the live app files from your working folder into this repo, commit and push
    python deploy.py deploy         package this repo, upload it, run deploy.sh on the server, health-check
    python deploy.py clean-server   list old release zips, old backups and unused Docker images; delete only after you confirm
    python deploy.py all            sync, then deploy, then clean-server

Options: --from FOLDER (sync source), --host user@ip, --key PATH, --yes (skip confirmations).
Never touched: the server's data folder, .env, deploy.sh, the Caddy container, and the running image.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import socket
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent
DOMAIN = "catrader.site"

# Files that make up the app. The server image is built from exactly these.
APP_FILES = [
    "app.py", "mcp_server.py", "ca_model.py", "ca_model_params.json",
    "ca_terminal.html", "terminal.html", "terminal_selector.html", "CA_Trader_Login.html", "fitness.html",
    "requirements.txt", "Dockerfile",
]
# Files you edit in your working folder (the live releases). `sync` brings these into the repo.
# mcp_server.py, ca_model*.*, ca_terminal.html and Dockerfile are maintained in the repo itself, so sync never overwrites them.
SYNC_FILES = ["app.py", "terminal.html", "terminal_selector.html", "CA_Trader_Login.html", "fitness.html", "requirements.txt"]
SYNC_FROM_DEFAULTS = [
    Path.home() / "Documents" / "CA_Trader" / "7",
    Path(r"c:\Users\SantoshMadnani\Documents\CA_Trader\7"),
    Path(r"D:\CA_Trader"),
]

# Known servers. The one catrader.site resolves to is picked automatically.
SERVERS = {
    "15.252.81.122": ["ca-trader-key.pem"],
    "80.225.236.5": ["oracle_key.key"],
}
KEY_DIRS = [REPO, REPO.parent, Path.home() / "Documents" / "CA_Trader", Path(r"c:\Users\SantoshMadnani\Documents\CA_Trader"), Path(r"D:\CA_Trader")]

REMOTE_HOME = "/home/ubuntu"
REMOTE_ZIP = "release.zip"
KEEP_BACKUPS = 3          # newest deploy.sh backups kept on the server
PROTECTED = ("ca-trader-final", "ca-trader-data", "deploy.sh", ".env", "caddy", "Caddyfile")


# ---------------------------------------------------------------- helpers
def say(msg: str = "") -> None:
    print(msg, flush=True)


def fail(msg: str) -> None:
    say(f"\nERROR: {msg}")
    sys.exit(1)


def confirm(question: str, yes: bool) -> bool:
    if yes:
        return True
    try:
        return input(f"{question} [y/N] ").strip().lower() in ("y", "yes")
    except EOFError:
        return False


def run(cmd: list[str], timeout: int = 300, check: bool = True, cwd: Path | None = None) -> subprocess.CompletedProcess:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, cwd=cwd)
    if check and r.returncode != 0:
        fail(f"{' '.join(cmd[:3])}… exited {r.returncode}\n{r.stdout}\n{r.stderr}")
    return r


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


# ---------------------------------------------------------------- server
class Server:
    def __init__(self, host: str | None, key: str | None):
        ip = None
        try:
            ip = socket.gethostbyname(DOMAIN)
        except OSError:
            pass
        self.domain_ip = ip
        if host:
            self.host = host if "@" in host else f"ubuntu@{host}"
        elif os.getenv("CA_TRADER_HOST"):
            self.host = os.environ["CA_TRADER_HOST"]
        elif ip in SERVERS:
            self.host = f"ubuntu@{ip}"
        else:
            fail(f"{DOMAIN} resolves to {ip}, which is not a known server. Pass --host ubuntu@<ip> --key <path>.")
        server_ip = self.host.split("@", 1)[1]
        self.key = key or os.getenv("CA_TRADER_KEY") or self._find_key(server_ip)
        if not self.key or not Path(self.key).exists():
            fail(f"No SSH key found for {server_ip}. Pass --key <path to {', '.join(SERVERS.get(server_ip, ['key']))}>.")

    @staticmethod
    def _find_key(ip: str) -> str | None:
        for name in SERVERS.get(ip, []):
            for d in KEY_DIRS:
                p = d / name
                if p.exists():
                    return str(p)
        return None

    def _opts(self) -> list[str]:
        return ["-i", self.key, "-o", "StrictHostKeyChecking=accept-new", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15"]

    def ssh(self, command: str, timeout: int = 300, check: bool = True) -> str:
        return run(["ssh", *self._opts(), self.host, command], timeout=timeout, check=check).stdout

    def scp(self, local: Path, remote: str) -> None:
        run(["scp", *self._opts(), str(local), f"{self.host}:{remote}"], timeout=600)


def health(paths=("/health", "/terminal", "/classic")) -> bool:
    ctx = ssl.create_default_context()
    ok = True
    for p in paths:
        url = f"https://{DOMAIN}{p}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ca-trader-deploy"})
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                say(f"  ok   {url} -> {resp.status}")
        except urllib.error.HTTPError as e:
            # /terminal and /classic redirect to the login page when signed out: that still proves they are served
            good = e.code in (301, 302, 303, 307, 308, 401)
            ok &= good
            say(f"  {'ok  ' if good else 'FAIL'} {url} -> {e.code}")
        except Exception as e:  # noqa: BLE001
            ok = False
            say(f"  FAIL {url} -> {e}")
    return ok


# ---------------------------------------------------------------- commands
def cmd_status(a) -> None:
    say(f"Repo: {REPO}")
    if (REPO / ".git").exists():
        say(run(["git", "status", "--short", "--branch"], cwd=REPO).stdout.rstrip())
        say(run(["git", "log", "--oneline", "-3"], cwd=REPO).stdout.rstrip())
    missing = [f for f in APP_FILES if not (REPO / f).exists()]
    say("App files: " + ("all present" if not missing else "MISSING " + ", ".join(missing)))
    src = sync_source(a, quiet=True)
    if src:
        diff = [f for f in SYNC_FILES if (src / f).exists() and (REPO / f).exists() and sha(src / f) != sha(REPO / f)]
        say(f"Working folder {src}: " + (", ".join(diff) + " differ from the repo (run sync)" if diff else "in sync with the repo"))
    srv = Server(a.host, a.key)
    say(f"\n{DOMAIN} -> {srv.domain_ip}; using {srv.host}")
    say(srv.ssh(f"df -h / | tail -1; du -sh {REMOTE_HOME}/* 2>/dev/null | sort -h | tail -12; sudo docker ps --format '{{{{.Names}}}}  {{{{.Image}}}}  {{{{.Status}}}}'", check=False))


def sync_source(a, quiet: bool = False) -> Path | None:
    cands = [Path(a.src)] if a.src else SYNC_FROM_DEFAULTS
    for c in cands:
        if (c / "app.py").exists() and c.resolve() != REPO:
            return c
    if not quiet:
        fail("Working folder not found. Pass --from <folder that holds your latest app.py>.")
    return None


def cmd_sync(a) -> None:
    src = sync_source(a)
    say(f"Sync {src} -> {REPO}")
    changed = []
    for f in SYNC_FILES:
        s, d = src / f, REPO / f
        if not s.exists():
            say(f"  skip {f} (not in working folder)")
            continue
        if d.exists() and sha(s) == sha(d):
            continue
        changed.append(f)
        say(f"  {'update' if d.exists() else 'add   '} {f} ({human(s.stat().st_size)})")
    if not changed:
        say("  already in sync")
    elif confirm(f"Copy {len(changed)} file(s) into the repo?", a.yes):
        for f in changed:
            shutil.copy2(src / f, REPO / f)
    else:
        say("  nothing copied")
        return
    if not (REPO / ".git").exists():
        say("This folder is not a git clone, so nothing was pushed.")
        return
    run(["git", "add", "-A"], cwd=REPO)
    if not run(["git", "status", "--porcelain"], cwd=REPO).stdout.strip():
        say("Git: nothing to commit.")
        return
    msg = "Sync app files from working folder: " + (", ".join(changed) if changed else "repo changes")
    run(["git", "commit", "-m", msg], cwd=REPO)
    if confirm("Push to GitHub (main)?", a.yes):
        run(["git", "pull", "--rebase", "origin", "main"], cwd=REPO)
        run(["git", "push", "origin", "HEAD:main"], cwd=REPO)
        say("Pushed.")


def cmd_deploy(a) -> None:
    missing = [f for f in APP_FILES if not (REPO / f).exists()]
    if missing:
        fail("missing app files: " + ", ".join(missing))
    for f in ("app.py", "mcp_server.py", "ca_model.py"):
        r = run([sys.executable, "-m", "py_compile", str(REPO / f)], check=False)
        if r.returncode != 0:
            fail(f"{f} does not compile:\n{r.stderr}")
    src = sync_source(a, quiet=True)
    if src and a.command == "deploy":
        stale = [f for f in SYNC_FILES if (src / f).exists() and sha(src / f) != sha(REPO / f)]
        if stale and not confirm("These differ from your working folder " + str(src) + ": " + ", ".join(stale)
                                 + ". Deploying now would ship the repo's copies. Run `python deploy.py sync` first. Deploy anyway?", False):
            return
    srv = Server(a.host, a.key)
    zpath = REPO / REMOTE_ZIP
    say(f"[1/4] Packaging {len(APP_FILES)} files")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in APP_FILES:
            z.write(REPO / f, f)
    say(f"      {zpath.name} {human(zpath.stat().st_size)}")
    if not confirm(f"Deploy to {srv.host} ({DOMAIN} -> {srv.domain_ip})?", a.yes):
        zpath.unlink(missing_ok=True)
        return
    try:
        say(f"[2/4] Uploading to {srv.host}:{REMOTE_HOME}/{REMOTE_ZIP}")
        srv.scp(zpath, f"{REMOTE_HOME}/{REMOTE_ZIP}")
        say("[3/4] Running deploy.sh (builds, tests the new image, then swaps it in)")
        say(srv.ssh(f"sudo {REMOTE_HOME}/deploy.sh {REMOTE_ZIP}", timeout=900))
        srv.ssh(f"rm -f {REMOTE_HOME}/{REMOTE_ZIP}", check=False)
    finally:
        zpath.unlink(missing_ok=True)
    say("[4/4] Health check")
    time.sleep(5)
    if not health():
        fail("health check failed. deploy.sh keeps the previous image; check `sudo docker logs ca-trader` on the server.")
    say("Deployed.")


def cmd_clean_server(a) -> None:
    srv = Server(a.host, a.key)
    say(f"Looking for leftovers on {srv.host}…")
    zips = [l for l in srv.ssh(f"ls -1 {REMOTE_HOME}/*.zip 2>/dev/null", check=False).split() if l.endswith(".zip")]
    backups = srv.ssh(f"ls -1dt {REMOTE_HOME}/ca-trader-backups/*/ 2>/dev/null", check=False).split()
    old_backups = backups[KEEP_BACKUPS:]
    running = srv.ssh("sudo docker inspect -f '{{.Image}}' ca-trader 2>/dev/null", check=False).strip()
    imgs = []
    for line in srv.ssh("sudo docker images --no-trunc --format '{{.ID}}|{{.Repository}}:{{.Tag}}|{{.CreatedAt}}|{{.Size}}'", check=False).splitlines():
        parts = line.split("|")
        if len(parts) == 4 and parts[1].startswith("ca-trader") and "caddy" not in parts[1]:
            imgs.append(parts)
    imgs.sort(key=lambda p: p[2], reverse=True)
    keep_ids = {running}
    for p in imgs:                                   # keep the newest image that is not running, for rollback
        if p[0] != running:
            keep_ids.add(p[0])
            break
    old_imgs = [p for p in imgs if p[0] not in keep_ids]
    targets = [z for z in zips if not any(x in z for x in PROTECTED)] + [b for b in old_backups if not any(x in b.rstrip("/").rsplit("/", 1)[-1] for x in PROTECTED)]
    if not targets and not old_imgs:
        say("Nothing to clean.")
    else:
        say("\nWill delete:")
        for t in targets:
            say("  " + t + "  " + srv.ssh(f"du -sh {t} | cut -f1", check=False).strip())
        for p in old_imgs:
            say(f"  image {p[1]} ({p[3]}, {p[2][:19]})")
        say(f"Keeps: the running image, the newest previous image, the {KEEP_BACKUPS} newest backups, data, .env, deploy.sh, Caddy.")
        if confirm("Delete these?", a.yes):
            if targets:
                srv.ssh("sudo rm -rf " + " ".join(f"'{t}'" for t in targets), check=False)
            for p in old_imgs:
                srv.ssh(f"sudo docker rmi {p[0]}", check=False)
            say("Deleted.")
    if confirm("Also remove dangling Docker layers and build cache (safe; nothing in use is touched)?", a.yes):
        say(srv.ssh("sudo docker image prune -f; sudo docker builder prune -f", check=False))
    say(srv.ssh("df -h / | tail -1", check=False))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["status", "sync", "deploy", "clean-server", "all"])
    ap.add_argument("--from", dest="src", help="working folder with your latest app files")
    ap.add_argument("--host", help="ssh target, e.g. ubuntu@15.252.81.122")
    ap.add_argument("--key", help="ssh private key file")
    ap.add_argument("--yes", action="store_true", help="answer yes to every confirmation")
    a = ap.parse_args()
    if a.command == "status":
        cmd_status(a)
    elif a.command == "sync":
        cmd_sync(a)
    elif a.command == "deploy":
        cmd_deploy(a)
    elif a.command == "clean-server":
        cmd_clean_server(a)
    else:
        cmd_sync(a)
        cmd_deploy(a)
        cmd_clean_server(a)


if __name__ == "__main__":
    main()
