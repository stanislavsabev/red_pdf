@echo off
setlocal enableextensions
set SELF=%~n0

if not exist "ui.py" (
    echo Application is missing files or is not installed correctly.
    exit /b
)

if not exist "venv\" (
    echo Python virtual environment not found in venv\ folder.
    echo Please run install.bat first.
    exit /b
)

REM Setup environment
chcp 65001
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
call venv\Scripts\activate.bat

REM Run the UI
call python -m ui

REM Keep window open if there's an error
if errorlevel 1 (
    pause
)