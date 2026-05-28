#!/bin/zsh
cd "$(dirname "$0")"
export PYTHONIOENCODING=utf-8
export XIANTU_HOST=0.0.0.0
python3 server.py
