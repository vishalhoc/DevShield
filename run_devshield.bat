@echo off
:: DevShield Silent Launcher
:: Finds pythonw.exe (no console) and runs devshield.py
setlocal

:: Try pythonw.exe first (no console window)
where pythonw.exe >nul 2>&1
if %errorlevel%==0 (
    start "" pythonw.exe "%~dp0devshield.py"
) else (
    :: Fallback to python.exe (console will be hidden by the script itself)
    start "" python.exe "%~dp0devshield.py"
)
