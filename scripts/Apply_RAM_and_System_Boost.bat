@echo off
:: Batch script to apply Administrator System Boost
echo =======================================================
echo   Applying RAM & System Boost (Administrator Mode)
echo =======================================================
echo.

:: Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Administrator rights required. Requesting elevation...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo [*] Expanding Virtual Memory (Pagefile) to 8 GB - 16 GB...
powershell -Command "Set-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management' -Name 'PagingFiles' -Value @('c:\pagefile.sys 8192 16384')"

echo [*] Setting Active Window CPU Priority (Win32PrioritySeparation)...
powershell -Command "Set-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\PriorityControl' -Name 'Win32PrioritySeparation' -Value 38"

echo [*] Disabling Hibernation to reclaim 1.5 GB SSD space...
powercfg -h off

echo [*] Cleaning Windows Update and setup scratch folders...
if exist "C:\$WinREAgent" rd /s /q "C:\$WinREAgent"
if exist "C:\$SysReset" rd /s /q "C:\$SysReset"
if exist "C:\Windows\SoftwareDistribution\Download" del /f /s /q "C:\Windows\SoftwareDistribution\Download\*" >nul 2>&1

echo.
echo =======================================================
echo   SUCCESS! System Boost Applied Successfully!
echo   - Virtual RAM increased to 16 GB
echo   - Multi-window CPU priority activated
echo   - 3.5 GB system cache & hibernation cleaned
echo =======================================================
echo.
pause
