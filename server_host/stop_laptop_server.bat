@echo off
cd /d "%~dp0\.."
title CA Trader - Laptop Server Stopper
echo ==========================================================
echo    STOPPING CA TRADER LAPTOP SERVER & TUNNEL
echo ==========================================================
python server_host\stop_laptop_server.py
echo.
pause

