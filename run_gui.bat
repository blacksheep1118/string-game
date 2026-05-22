@echo off
title XianTu - Cultivation Game

echo.
echo ========================================
echo   XianTu - Text Cultivation Game
echo ========================================
echo.
echo Starting server...
echo Open http://127.0.0.1:5000 in your browser
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

python -c "import flask" 2>nul || pip install flask -q
start http://127.0.0.1:5000
python server.py
pause
