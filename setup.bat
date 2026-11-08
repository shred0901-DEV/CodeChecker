@echo off
setlocal
cd /d "%~dp0"

echo ========================================================
echo   CodeChecker - Environment Setup
echo ========================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found.
    echo Please install Python 3.10 or higher.
    pause
    exit /b 1
)

echo Installing dependencies (pywebview, semgrep, requests, etc.)...
python -m pip install -r requirements.txt

echo.
echo ========================================================
echo   Setup completed!
echo   Double click run.bat to start the application.
echo ========================================================
echo.
pause
