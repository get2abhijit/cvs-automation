@echo off
  
set exe_path="C:\code\learning\python\cvs-automation\cvs-report-generator\dist\cvs_config.exe"  
set days=1
set output="C:\code\assyst\dev\cvs-reports"
set workspace_path="C:\code\assyst\dev"

%exe_path% --days=%days% --path=%workspace_path%

