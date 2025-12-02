@echo off
set SELF=%~n0

:: ===================================================
:: 4. CREATE & ACTIVATE VIRTUAL ENVIRONMENT
:: ===================================================
if exist "..\venv" (
    echo Virtual environment already exists.
    exit /b
) else (
    cd ..
    echo Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo Failed to create virtual environment.
        set EXIT_CODE=1
        goto :end
    )
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
    exit /b
)

echo.
echo ================================================
echo Setup complete!
echo ================================================
