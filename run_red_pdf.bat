@echo off
setlocal enableextensions
set SELF=%~n0

if not exist "ui.py" (
    echo Looks like installation was not performed.
    echo Right-click on install.bat and choose 'Run as administrator'...
    exit /b
)

if not exist "venv\" (
    echo Python virtual environment not found in venv\ folder.
    echo Please run install.bat first.
    exit /b
)

REM Activate the virtual environment
call venv\Scripts\activate.bat

REM Run the UI
python -m ui

REM Keep window open if there's an error
if errorlevel 1 (
    pause
)