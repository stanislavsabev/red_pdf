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
    goto :end
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

if %PYTHON_FOUND% neq 0 (
    echo Python not found on this system.
    set /p INSTALL_PY="Install Python 3.12 now? (Y/N): "

    if /I "%INSTALL_PY%"=="Y" (
        echo Downloading Python 3.12 installer...

        set PYTHON_URL=https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe
        set PYTHON_INSTALLER=python-3.12.0-amd64.exe

        curl -L "%PYTHON_URL%" -o "%PYTHON_INSTALLER%"
        if not exist "%PYTHON_INSTALLER%" (
            echo Failed to download Python installer.
            set EXIT_CODE=1
            goto :end
        )

        echo Running Python installer...
        "%PYTHON_INSTALLER%" /quiet InstallAllUsers=1 PrependPath=1 Include_pip=1

        echo Waiting for installation to finish...
        timeout /t 5 >nul

        python --version >nul 2>&1
        if %errorlevel% neq 0 (
            echo Python installation failed.
            set EXIT_CODE=1
            goto :end
        )

    ) else (
        echo Python installation aborted.
        goto :end
    )
)

echo Python found:
python --version
echo.


:: ===================================================
:: 2. CHECK FOR TESSERACT OCR
:: ===================================================
echo Checking for Tesseract installation...

where tesseract >nul 2>&1
set TESS_FOUND=%errorlevel%

if %TESS_FOUND% neq 0 (
    echo Tesseract not found on this system.
    set /p INSTALL_TESS="Install Tesseract OCR now? (Y/N): "

    if /I "%INSTALL_TESS%"=="Y" (
        echo Downloading Tesseract installer...

        :: Official UB Mannheim build (most used on Windows)
        set TESS_URL=https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.3.4.20240503.exe
        set TESS_INSTALLER=tesseract-ocr-w64-setup-5.3.4.20240503.exe

        curl -L "%TESS_URL%" -o "%TESS_INSTALLER%"
        if not exist "%TESS_INSTALLER%" (
            echo Failed to download Tesseract installer.
            set EXIT_CODE=1
            goto :end
        )

        echo Running Tesseract installer...
        "%TESS_INSTALLER%" /SILENT

        echo Waiting for installation...
        timeout /t 5 >nul

        where tesseract >nul 2>&1
        if %errorlevel% neq 0 (
            echo Tesseract installation failed.
            set EXIT_CODE=1
            goto :end
        )
    ) else (
        echo Tesseract installation skipped.
    )
)

echo Tesseract found:
tesseract --version | findstr /C:"tesseract"
echo.


:: ===================================================
:: 3. DOWNLOAD GITHUB PROJECT ZIP
:: ===================================================
echo Checking for Red PDF installation...

if not exist "ui.py" (


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
    powershell -Command "Expand-Archive -Path '%ZIP_FILE%' -DestinationPath . -Force"
    del "%ZIP_FILE%"

    echo Repository extracted.
    echo.


    :: ===================================================
    :: 4. IDENTIFY EXTRACTED FOLDER
    :: ===================================================
    for /d %%D in (*-main) do set PROJECT_DIR=%%D

    if not defined PROJECT_DIR (
        echo Could not locate extracted project folder.
        set EXIT_CODE=1
        goto :end
    )

    echo Project directory found: %PROJECT_DIR%
    cd "%PROJECT_DIR%"

) else (
    echo Red PDF installation skipped.
)


:: ===================================================
:: 5. CREATE & ACTIVATE VIRTUAL ENVIRONMENT
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
    echo Creating virtual environment skipped.

)

echo Activating virtual environment...
call venv\Scripts\activate


:: ===================================================
:: 6. INSTALL PYTHON DEPENDENCIES
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
if %EXIT_CODE% equ 1 (
    pause
)
exit /b