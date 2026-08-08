@echo off
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set XIANTU_HOST=0.0.0.0
python launcher.py web --lan
pause
