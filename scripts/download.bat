@echo off
setlocal enableextensions
set SELF=%~n0
set EXIT_CODE=

:: -----------------------------------
::  Ensure script runs as Administrator
:: -----------------------------------
>nul 2>&1 net session
if %errorLevel% neq 0 (
    echo This script requires administrator rights.
    echo Relaunching with admin privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo.
echo ================================================
echo       Python + Tesseract Setup Script
echo ================================================
echo.

:: ===================================================
:: 1. CHECK FOR PYTHON
:: ===================================================
echo Checking for Python installation...

python --version >nul 2>&1
set PYTHON_FOUND=%errorlevel%

if !PYTHON_FOUND! neq 0 (
    echo Python not installed on this system.
    set PYTHON_INSTALLER="python-3.12.0-amd64.exe"
    if not exist "%TESS_INSTALLER%" (
        echo Downloading Python 3.12 installer...

        set PYTHON_URL=https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe
        curl -L "%PYTHON_URL%" -o "%PYTHON_INSTALLER%"
        if not exist "%PYTHON_INSTALLER%" (
            echo Failed to download Python installer.
            set EXIT_CODE=1
            goto :end
        )
    ) else (
        echo Python download skipped.
    )
) else (
    echo Python found:
    python --version
    echo.
)

:: ===================================================
:: 2. CHECK FOR TESSERACT OCR
:: ===================================================
echo Checking for Tesseract download...
set TESS_INSTALLER="tesseract-ocr-w64-setup-5.3.4.20240503.exe"

if not exist "%TESS_INSTALLER%" (
    echo Tesseract not found.
    echo Downloading Tesseract installer...

    set TESS_URL=https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.3.4.20240503.exe
    curl -L "%TESS_URL%" -o "%TESS_INSTALLER%"
    if not exist "%TESS_INSTALLER%" (
        echo Failed to download Tesseract installer.
        set EXIT_CODE=1
        goto :end
    )

) else (
    echo Tesseract download skipped.
)



:: ===================================================
:: 3. DOWNLOAD GITHUB PROJECT ZIP
:: ===================================================
echo Checking for Red PDF installation...

if exist "version.py" (
    echo Red PDF installation skipped.
) else (
    set ZIP_URL=https://github.com/stanislavsabev/red_pdf/archive/refs/heads/main.zip
    set ZIP_FILE=red_pdf-main.zip

    echo Downloading GitHub project...
    curl -L "%ZIP_URL%" -o "%ZIP_FILE%"
    if not exist "%ZIP_FILE%" (
        echo Failed to download GitHub zip.
        set EXIT_CODE=1
        goto :end
    )

    echo Unpacking zip...
    powershell -Command "Expand-Archive -Path '%!%ZIP_FILE%!%' -DestinationPath . -Force"

    del "%ZIP_FILE%"
    echo Repository extracted.
    echo.

    :: Identify extracted folder
    for /d %%D in (*-main) do set PROJECT_DIR=%%D

    if not defined PROJECT_DIR (
        echo Could not locate extracted project folder.
        set EXIT_CODE=1
        goto :end
    )

    echo Project directory found: %PROJECT_DIR%

)


:: ===================================================
:: 4. CREATE & ACTIVATE VIRTUAL ENVIRONMENT
:: ===================================================
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo Failed to create virtual environment.
        set EXIT_CODE=1
        goto :end
    )
) else (
    echo Virtual environment already exists.
)

echo Activating virtual environment...
call venv\Scripts\activate


:: ===================================================
:: 5. INSTALL PYTHON DEPENDENCIES
:: ===================================================
if exist requirements.txt (
    echo Installing packages from requirements.txt...
    pip install --upgrade pip
    pip install -r requirements.txt
) else (
    echo No requirements.txt found.
)

echo.
echo ================================================
echo Setup complete!
echo ================================================

:end
echo.
echo Exiting with code: %EXIT_CODE%
pause
exit /b %EXIT_CODE%
