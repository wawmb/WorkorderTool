@echo off
setlocal
cd /d "%~dp0.."
cd src

set "PY="
where py >nul 2>&1
if not errorlevel 1 set "PY=py -3"
if not defined PY (
    where python >nul 2>&1
    if not errorlevel 1 set "PY=python"
)
if not defined PY (
    echo [ERROR] Python not found in PATH.
    echo Please install Python 3.8+ first.
    echo.
    pause
    exit /b 1
)

if not exist "..\.venv" (
    echo [setup] Creating virtual environment .venv
    %PY% -m venv "..\.venv"
)
if not exist "..\.venv\Scripts\python.exe" (
    echo [ERROR] Failed to create .venv.
    echo.
    pause
    exit /b 1
)

set "VENV_PY=..\.venv\Scripts\python.exe"
echo [setup] Installing build dependencies...
%VENV_PY% -m pip install --upgrade pip
%VENV_PY% -m pip install -r requirements.txt
%VENV_PY% -m pip install pyinstaller

echo [build] Running PyInstaller...
%VENV_PY% -m PyInstaller --noconfirm --clean --distpath ..\dist --workpath ..\build WorkorderTool.spec
if errorlevel 1 (
    echo [ERROR] Build failed. Check output above.
    echo.
    pause
    exit /b 1
)

echo.
echo Build OK. Output: dist\WorkorderTool.exe
echo.
pause
endlocal
