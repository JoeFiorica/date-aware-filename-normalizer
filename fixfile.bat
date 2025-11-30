@echo off
setlocal

REM Change to the directory of this batch file
cd /d "%~dp0"

REM Run the Python script in this same directory
python fixfile.py

pause
