@echo off
cd /d "%~dp0\.."
title CA Trader - Laptop Server Runner
echo ==========================================================
echo    STARTING CA TRADER LAPTOP SERVER
echo ==========================================================
python server_host\start_laptop_server.py
pause

