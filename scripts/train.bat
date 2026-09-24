@echo off
REM Retrain the phishing model and leave it running unattended. Just run: scripts\train.bat
REM
REM   scripts\train.bat                                -> train on ml\data\processed as-is
REM   scripts\train.bat --extra-dir "C:/path/to/data"  -> re-run preprocess.py first, then train
REM
REM Any arguments are passed to preprocess.py (together with --include-mock).
REM Warning: preprocess overwrites ml\data\processed. Without --extra-dir you get only the
REM small built-in datasets, so pass the same --extra-dir used for the current 39,320 rows.
REM
REM Progress is shown on screen and also saved to ml\results\train_YYYYMMDD_HHMMSS.log
setlocal
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set "PY=%~dp0..\.venv\Scripts\python.exe"
if not exist "%PY%" (
    echo Cannot find %PY%
    echo Create it first: python -m venv .venv ^&^& .venv\Scripts\pip install -e ".[ml,dev]"
    set CODE=1
    goto end
)

cd /d "%~dp0..\ml"
if not exist results mkdir results
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set STAMP=%%i
set "LOG=%CD%\results\train_%STAMP%.log"
echo Started %DATE% %TIME%
echo Log: %LOG%
echo This can take several minutes. You can leave this window open and walk away.
echo.

if not "%~1"=="" (
    echo [1/2] preprocess.py --include-mock %*
    "%PY%" "%~dp0run_logged.py" "%LOG%" "%PY%" -u preprocess.py --include-mock %*
    if errorlevel 1 goto failed
) else (
    echo [1/2] preprocess skipped, using existing ml\data\processed
)

echo [2/2] train.py
"%PY%" "%~dp0run_logged.py" "%LOG%" "%PY%" -u train.py
if errorlevel 1 goto failed

echo.
echo Finished %DATE% %TIME%.
set CODE=0
goto end

:failed
set CODE=%ERRORLEVEL%
echo.
echo Training failed with exit code %CODE%. See the messages above.

:end
echo.
pause
exit /b %CODE%
