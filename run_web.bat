@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set XIANTU_HOST=0.0.0.0
python server.py
pause
