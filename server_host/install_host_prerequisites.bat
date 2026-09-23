@echo off
cd /d "%~dp0\.."
echo ==========================================================
echo    CA TRADER - INSTALLING LAPTOP HOST PREREQUISITES
echo ==========================================================
python server_host\install_host_prerequisites.py
pause
