@echo off
setlocal
cd /d "%~dp0.."

echo [clean] Removing build artifacts and temp files...
if exist "build"           rmdir /s /q "build"
if exist "dist"            rmdir /s /q "dist"
if exist ".venv"           rmdir /s /q ".venv"
if exist "__pycache__"     rmdir /s /q "__pycache__"
if exist "src\__pycache__" rmdir /s /q "src\__pycache__"
for /r %%f in (*.pyc) do del /f /q "%%f" >nul 2>&1
echo [clean] Done. Source (src/) and scripts (scripts/) kept.
echo.
pause
endlocal
