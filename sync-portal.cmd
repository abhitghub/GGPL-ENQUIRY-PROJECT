@echo off
REM Double-click this on the SERVER PC to pull the latest code and restart the
REM portal. Data is untouched. Users just refresh their browser afterwards.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0sync-portal.ps1"
echo.
pause