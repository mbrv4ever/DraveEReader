@echo off
setlocal
cd /d "%~dp0"
title DraveEReader - herstellen
echo Dit wist de installatiemap (.venv) en bouwt alles opnieuw op.
echo.
choice /m "Doorgaan"
if errorlevel 2 goto :einde
if exist ".venv" rmdir /s /q ".venv"
echo .venv verwijderd. Start nu run.bat opnieuw voor een schone installatie.
:einde
pause
endlocal
