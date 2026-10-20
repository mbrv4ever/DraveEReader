@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title DraveEReader
set "VENV=.venv"

set "PY="
if not defined PY ( py -3.13 -c "import sys" >nul 2>&1 && set "PY=py -3.13" )
if not defined PY ( py -3.12 -c "import sys" >nul 2>&1 && set "PY=py -3.12" )
if not defined PY ( py -3.11 -c "import sys" >nul 2>&1 && set "PY=py -3.11" )
if not defined PY ( py -3.10 -c "import sys" >nul 2>&1 && set "PY=py -3.10" )
if not defined PY ( python -c "import sys" >nul 2>&1 && set "PY=python" )
if not defined PY (
  echo Geen geschikte Python gevonden ^(3.10 t/m 3.13^).
  echo Installeer Python van https://www.python.org en probeer opnieuw.
  pause
  exit /b 1
)

if not exist "%VENV%\Scripts\python.exe" (
  echo Eerste keer starten: onderdelen installeren. Dit kan even duren...
  %PY% -m venv "%VENV%"
  "%VENV%\Scripts\python.exe" -m pip install --upgrade pip
  "%VENV%\Scripts\python.exe" -m pip install --only-binary=:all: -r requirements.txt
)

REM Zelfherstel: zijn de kernonderdelen aanwezig?
"%VENV%\Scripts\python.exe" -c "import PyQt6, fitz, numpy" >nul 2>&1
if errorlevel 1 (
  echo Onderdelen herstellen...
  "%VENV%\Scripts\python.exe" -m pip install --only-binary=:all: -r requirements.txt
)

start "" "%VENV%\Scripts\pythonw.exe" app.py %*
endlocal
