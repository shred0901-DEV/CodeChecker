@echo off
setlocal
cd /d "%~dp0"

echo ========================================================
echo   CodeChecker - Source Code Vulnerability Scanner
echo ========================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found.
    echo Please install Python 3.10 or higher.
    echo https://www.python.org/
    echo.
    pause
    exit /b 1
)

python -c "import webview, semgrep" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing required dependencies...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
    echo.
)

echo Starting CodeChecker...
python main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Application exited with error code %errorlevel%.
    pause
)
