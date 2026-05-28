@echo off
title Build XianTu EXE

echo.
echo ========================================
echo   Building XianTu Standalone EXE
echo ========================================
echo.

python -c "import PyInstaller" 2>nul || pip install pyinstaller -q

echo [*] Building...
echo.

pyinstaller --noconfirm XianTu.spec

echo.
echo ========================================
echo   Done! dist\XianTu.exe
echo ========================================
pause
