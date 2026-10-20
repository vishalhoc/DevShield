@echo off
:: TurboBoost - Game & Dev Mode Optimizer Launcher
setlocal
cd /d "%~dp0"
title TurboBoost

python "%~dp0turboboost.py"
if %errorlevel% neq 0 (
    echo.
    echo TurboBoost exited with code %errorlevel%.
    pause
)
