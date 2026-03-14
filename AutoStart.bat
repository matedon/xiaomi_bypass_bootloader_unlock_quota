@echo off
setlocal

title Xiaomi AutoStart Launcher

rem Always run from this script's directory
cd /d "%~dp0"

if not exist "AutoStart.py" (
    echo [ERR] AutoStart.py was not found in:
    echo       %CD%
    pause
    exit /b 1
)

rem Prefer Python Launcher on Windows, then fallback to python.exe
where py >nul 2>nul
if %errorlevel%==0 (
    echo [i] Starting with: py AutoStart.py
    py "AutoStart.py"
    set "RUN_ERR=%errorlevel%"
    goto :after_run
)

where python >nul 2>nul
if %errorlevel%==0 (
    echo [i] Starting with: python AutoStart.py
    python "AutoStart.py"
    set "RUN_ERR=%errorlevel%"
    goto :after_run
)

echo [ERR] Python was not found. Install Python 3 and try again.
echo       https://www.python.org/downloads/
pause
exit /b 1

:after_run
if not "%RUN_ERR%"=="0" (
    echo.
    echo [ERR] AutoStart.py exited with code %RUN_ERR%.
    pause
    exit /b %RUN_ERR%
)

endlocal
exit /b 0
