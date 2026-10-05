@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch_character_call.ps1"
if errorlevel 1 (
    echo.
    echo Character Call could not be launched. See the message above.
    pause
)
