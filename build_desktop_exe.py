#!/usr/bin/env python3
"""
build_desktop_exe.py
Build script for packaging CA Trader into a native Windows desktop client (.exe).
"""

from __future__ import annotations

import sys
import shutil
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
APP_DIR = ROOT_DIR / "app"
STATIC_DIR = APP_DIR / "static"
ICON_PATH = STATIC_DIR / "ca_trader.ico"

print("=" * 70)
print("  CA TRADER NATIVE WINDOWS DESKTOP CLIENT BUILDER")
print("=" * 70)

assert (APP_DIR / "desktop_app.py").exists(), "desktop_app.py not found!"
assert ICON_PATH.exists(), f"Icon not found at {ICON_PATH}!"

print(f"[*] Workspace Root: {ROOT_DIR}")
print(f"[*] App Directory: {APP_DIR}")
print(f"[*] Icon: {ICON_PATH}")

hidden_imports = [
    "webview",
    "webview.platforms.winforms",
    "clr",
    "pythonnet",
]

cmd = [
    sys.executable,
    "-m", "PyInstaller",
    "--name=CA_Trader",
    "--noconsole",
    f"--icon={ICON_PATH}",
    "--onedir",
    "--clean",
    "--noconfirm",
    f"--distpath={ROOT_DIR / 'dist'}",
    f"--workpath={ROOT_DIR / 'build'}",
]

for imp in hidden_imports:
    cmd.extend(["--hidden-import", imp])

cmd.append(str(APP_DIR / "desktop_app.py"))

print(f"\n[*] Running PyInstaller compilation...")
res = subprocess.run(cmd, cwd=str(APP_DIR))

if res.returncode != 0:
    print(f"\n[!] Compilation failed with exit code {res.returncode}")
    sys.exit(res.returncode)

dist_app_dir = ROOT_DIR / "dist" / "CA_Trader"
print(f"\n[*] Copying static icon assets into {dist_app_dir}...")

dst_static = dist_app_dir / "static"
dst_static.mkdir(exist_ok=True, parents=True)
if ICON_PATH.exists():
    shutil.copy2(ICON_PATH, dst_static / "ca_trader.ico")

exe_path = dist_app_dir / "CA_Trader.exe"
print("\n" + "=" * 70)
print("  BUILD SUCCESSFUL!")
print(f"  Native Executable: {exe_path}")
print("=" * 70)

# Create a desktop shortcut script
ps_script = f"""
$WshShell = New-Object -comObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath('Desktop')
$Shortcut = $WshShell.CreateShortcut("$DesktopPath\\CA Trader.lnk")
$Shortcut.TargetPath = "{exe_path}"
$Shortcut.WorkingDirectory = "{dist_app_dir}"
$Shortcut.IconLocation = "{dist_app_dir}\\static\\ca_trader.ico, 0"
$Shortcut.Description = "CA Trader - Institutional Trading Terminal"
$Shortcut.Save()
Write-Host "Desktop shortcut created: $DesktopPath\\CA Trader.lnk"
"""

shortcut_script_path = ROOT_DIR / "create_desktop_shortcut.ps1"
shortcut_script_path.write_text(ps_script, encoding="utf-8")

try:
    subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(shortcut_script_path)], check=True)
    print("[*] Successfully updated 'CA Trader' shortcut on your Windows Desktop!")
except Exception as e:
    print(f"[!] Could not auto-create desktop shortcut: {e}")
