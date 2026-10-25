@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 setup.py install %*
  goto done
)
where python >nul 2>nul
if not errorlevel 1 (
  python setup.py install %*
  goto done
)
echo Python 3.11 or newer is required. Install it from https://www.python.org/downloads/
:done
echo.
pause
