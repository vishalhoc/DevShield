@echo off
:: TurboBoost - Game & Dev Mode Optimizer Launcher
:: Requests Admin elevation and starts TurboBoost GUI
setlocal
cd /d "%~dp0"

:: Try pythonw.exe first (clean, no cmd window)
where pythonw.exe >nul 2>&1
if %errorlevel%==0 (
    start "" pythonw.exe "%~dp0turboboost.py"
) else (
    start "" python.exe "%~dp0turboboost.py"
)
