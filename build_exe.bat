@echo off
setlocal
cd /d "%~dp0"
title Build XianTu EXE

echo.
echo ========================================
echo   Building XianTu Standalone EXE
echo ========================================
echo.

python -m pip install -r requirements-build.txt -q
if errorlevel 1 (
  echo [ERROR] Could not install build dependencies.
  exit /b 1
)

echo [*] Building...
echo.

python -m PyInstaller --noconfirm XianTu.spec
if errorlevel 1 (
  echo [ERROR] PyInstaller build failed.
  exit /b 1
)

echo.
echo ========================================
echo   Done! dist\XianTu.exe
echo ========================================
pause
