@echo off
REM One-command setup for PhishMail. Just run: scripts\setup.bat
REM This wrapper exists so nobody has to remember the ExecutionPolicy flag.
setlocal
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1" %*
set CODE=%ERRORLEVEL%
echo.
if not "%CODE%"=="0" echo Setup failed with exit code %CODE%. See the messages above.
pause
exit /b %CODE%
