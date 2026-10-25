@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0artifacts\ClearHome-Windows-Setup.exe" (
  start "" "%~dp0artifacts\ClearHome-Windows-Setup.exe"
  exit /b
)
echo Download ClearHome-Windows-Setup.exe from:
echo https://github.com/Er-Arif/clear-home-fire-tv/releases/latest
echo The standalone application prepares Python and ADB automatically.
pause
