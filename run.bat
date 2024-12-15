@echo off
setlocal

REM Check for Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH
    exit /b 1
)

REM Create logs directory if it doesn't exist
if not exist logs mkdir logs

REM Activate virtual environment if it exists
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else (
    echo Virtual environment not found. Creating one...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
)

REM Parse command line arguments
if "%1"=="--debug" (
    echo Starting in debug mode...
    echo Debug log will be written to logs\debug.log
    python src/main.py --debug 2>>logs\debug.log
) else if "%1"=="--help" (
    echo Usage:
    echo   run.bat [options]
    echo.
    echo Options:
    echo   --debug    Start application in debug mode
    echo   --help     Show this help message
) else (
    echo Starting in normal mode...
    python src/main.py
)

REM Check exit code
if errorlevel 1 (
    echo Application exited with error code %errorlevel%
    if "%1"=="--debug" (
        echo Check logs\debug.log for details
    )
)

REM Deactivate virtual environment
deactivate

endlocal 