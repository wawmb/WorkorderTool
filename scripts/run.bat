@echo off
setlocal
cd /d "%~dp0.."
cd src

title WorkorderTool

set "PY="
where python >nul 2>&1
if %errorlevel%==0 (
    set "PY=python"
    goto CHECK
)
where py >nul 2>&1
if %errorlevel%==0 (
    set "PY=py -3"
    goto CHECK
)
echo [ERROR] Python not found. Please install Python 3.8+ and add to PATH.
echo.
pause
exit /b 1

:CHECK
echo [INFO] Using: %PY%

%PY% -c "import requests" >nul 2>&1
if %errorlevel%==0 (
    echo [INFO] requests OK.
) else (
    echo [INFO] Installing dependencies...
    %PY% -m pip install -r requirements.txt
)

:LAUNCH
echo [INFO] Starting WorkorderTool...
%PY% workorder_app.py
set "EXITCODE=%errorlevel%"
if %EXITCODE% neq 0 (
    echo [ERROR] WorkorderTool exited with code %EXITCODE%
    echo.
    pause
)
endlocal
