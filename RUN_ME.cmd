@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if errorlevel 1 goto use_python
py -3.12 -c "import sys" >nul 2>&1
if errorlevel 1 goto use_python
py -3.12 bootstrap.py
if errorlevel 1 goto failed
exit /b 0
:use_python
python bootstrap.py
if errorlevel 1 goto failed
exit /b 0
:failed
echo.
echo GymPulse could not start. Python 3.12 is required.
echo First-time dependency installation also needs internet access.
echo Read START_HERE.md for setup steps and diagnostics.
pause
exit /b 1
