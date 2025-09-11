@echo off
REM CVS Commit Analyzer - Windows Batch Runner
REM This script provides an easy way to run the CVS analyzer on Windows

setlocal enabledelayedexpansion

echo ============================================
echo CVS Commit Analyzer
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.7+ and try again
    pause
    exit /b 1
)

REM Check if required files exist
if not exist "cvs_analyzer.py" (
    echo Error: cvs_analyzer.py not found in current directory
    pause
    exit /b 1
)

if not exist "cvs_config.py" (
    echo Error: cvs_config.py not found in current directory
    pause
    exit /b 1
)

REM Install required Python packages if needed
echo Checking Python dependencies...
python -c "import pandas, openpyxl" >nul 2>&1
if errorlevel 1 (
    echo Installing required packages...
    pip install pandas openpyxl
    if errorlevel 1 (
        echo Error: Failed to install required packages
        echo Please run: pip install pandas openpyxl
        pause
        exit /b 1
    )
)

REM Check if we're in a CVS working directory
if not exist "CVS" (
    echo Warning: CVS directory not found
    echo Make sure you're running this from a CVS working directory
    echo.
)


echo Running quick analysis (last 1 days)...
python cvs_config.py --days 1 --window 1 --path "C:\code\assyst\dev"

if errorlevel 1 
(
    echo Analysis failed with errors.
) else 
(
    echo Analysis completed successfully!
    exit /b 0
)