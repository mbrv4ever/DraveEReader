@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title DraveEReader - EXE bouwen

echo ============================================
echo   DraveEReader - een echte .EXE bouwen
echo ============================================
echo.

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

echo [1/4] Benodigdheden installeren...
%PY% -m pip install --upgrade pip
%PY% -m pip install --only-binary=:all: -r requirements.txt
%PY% -m pip install --only-binary=:all: pyinstaller

echo [2/4] Icoon (her)maken...
if not exist "assets\app.ico" %PY% maak_icoon.py

echo [3/4] PyInstaller draait... dit kan enkele minuten duren.
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
%PY% -m PyInstaller --noconfirm --clean DraveEReader.spec

echo [4/4] Resultaat controleren...
if exist "dist\DraveEReader.exe" (
  echo.
  echo ============================================
  echo   KLAAR! De .EXE is gemaakt:
  echo   "%~dp0dist\DraveEReader.exe"
  echo ============================================
  echo Het venster van de map wordt geopend.
  explorer "dist"
) else (
  echo.
  echo ============================================
  echo   LET OP: er is GEEN dist\DraveEReader.exe gemaakt.
  echo   Lees de meldingen hierboven om te zien wat misging.
  echo ============================================
)
echo.
pause
endlocal
