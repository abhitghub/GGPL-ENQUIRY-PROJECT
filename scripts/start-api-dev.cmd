@echo off
setlocal

set "REPO_ROOT=%~dp0.."
set "PYTHONPATH=%REPO_ROOT%;%REPO_ROOT%\packages;%REPO_ROOT%\apps\api"

cd /d "%REPO_ROOT%\apps\api"
"%REPO_ROOT%\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
