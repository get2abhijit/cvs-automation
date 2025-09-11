@echo off

REM usage: cvs_config.exe [-h] [--days DAYS | --start START] [--end END] [--author AUTHOR] [--window WINDOW]
                      REM [--output OUTPUT] [--path PATH] [--verbose]

REM Analyze CVS commits and group related changes

REM options:
  REM -h, --help       show this help message and exit
  REM --days DAYS      Analyze last N days (default: 30)
  REM --start START    Start date (YYYY-MM-DD format)
  REM --end END        End date (YYYY-MM-DD format, used with --start)
  REM --author AUTHOR  Filter by specific author/username
  REM --window WINDOW  Time window in minutes for grouping commits (default: 10)
  REM --output OUTPUT  Output Excel filename (default: auto-generated)
  REM --path PATH      CVS repository path (default: current directory)
  REM --verbose        Enable verbose output

REM Examples:
  REM # Analyze last 30 days
  REM python cvs_config.py --days 30

  REM # Analyze specific date range
  REM python cvs_config.py --start 2024-01-01 --end 2024-02-01

  REM # Analyze specific author
  REM python cvs_config.py --author john.doe --days 60

  REM # Custom time window for grouping
  REM python cvs_config.py --days 14 --window 5

  REM # Specify output file
  REM python cvs_config.py --days 7 --output weekly_analysis.xlsx
  
set exe_path="C:\code\assyst\cvs-report-generator\dist\cvs_config.exe"  
set days=10
set output="C:\code\assyst\dev\cvs-reports"
set workspace_path="C:\code\assyst\dev"

%exe_path% --days=%days% --path=%workspace_path%

