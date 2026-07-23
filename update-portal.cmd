@echo off
REM One-click release: rebuilds the portal with the latest code and restarts it.
REM Users on the LAN just refresh their browser afterwards. Data is untouched.
cd /d "%~dp0"
echo Rebuilding and restarting the GGPL Quote portal...
docker compose -f docker-compose.prod.yml up -d --build
if %errorlevel% neq 0 (
  echo.
  echo BUILD FAILED - the previous version is still running. See errors above.
  pause
  exit /b 1
)
echo.
echo Done. Ask users to refresh their browser (http://192.168.0.138:3000).
pause
