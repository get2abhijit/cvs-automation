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

REM Show menu options
:menu
echo Choose an analysis option:
echo.
echo 1. Quick analysis (last 1 day)
echo 2. Standard analysis (last 7 days) 
echo 3. Extended analysis (last 30 days)
echo 4. Custom date range
echo 5. Analyze specific author
echo 6. Advanced options
echo 7. Exit
echo.
set /p choice="Enter your choice (1-7): "

if "%choice%"=="1" goto quick
if "%choice%"=="2" goto standard
if "%choice%"=="3" goto extended
if "%choice%"=="4" goto custom_range
if "%choice%"=="5" goto specific_author
if "%choice%"=="6" goto advanced
if "%choice%"=="7" goto exit
goto invalid_choice

:quick
echo Running quick analysis (last 1 days)...
python cvs_config.py --days 1 --window 1
goto results

:standard
echo Running standard analysis (last 7 days)...
python cvs_config.py --days 7 --window 1
goto results

:extended
echo Running extended analysis (last 30 days)...
python cvs_config.py --days 30 --window 1
goto results

:custom_range
echo.
echo Enter date range (YYYY-MM-DD format):
set /p start_date="Start date: "
set /p end_date="End date: "
echo Running custom analysis from %start_date% to %end_date%...
python cvs_config.py --start %start_date% --end %end_date%
goto results

:specific_author
echo.
set /p author="Enter author username: "
set /p days="Enter number of days to analyze (default 30): "
if "%days%"=="" set days=30
echo Running analysis for author: %author% (last %days% days)...
python cvs_config.py --author %author% --days %days%
goto results

:advanced
echo.
echo Advanced Options:
set /p days="Days to analyze (default 30): "
if "%days%"=="" set days=30

set /p author="Author filter (leave empty for all): "

set /p window="Time window for grouping in minutes (default 1): "
if "%window%"=="" set window=1

set /p output="Output filename (leave empty for auto): "

set /p workspace_path="Local workspace path (leave empty for auto): "
if "%workspace_path%"=="" set workspace_path=.

set cmd_line=--days %days% --window %window% --path %workspace_path%
if not "%author%"=="" set cmd_line=!cmd_line! --author %author%
if not "%output%"=="" set cmd_line=!cmd_line! --output %output%

echo Running advanced analysis...
python cvs_config.py %cmd_line%
goto results

:results
echo.
if errorlevel 1 (
    echo Analysis failed with errors.
) else (
    echo Analysis completed successfully!
    echo Check the generated Excel file for results.
)
echo.
echo Press any key to return to menu...
pause >nul
echo.
goto menu

:invalid_choice
echo Invalid choice. Please enter a number from 1-7.
goto menu

:exit
echo.
echo Thank you for using CVS Commit Analyzer!
pause
exit /b 0