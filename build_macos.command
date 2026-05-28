#!/bin/zsh
cd "$(dirname "$0")"
python3 -m pip show pyinstaller >/dev/null 2>&1 || python3 -m pip install pyinstaller
python3 -m PyInstaller --noconfirm XianTu.spec
echo "Done: dist/XianTu"
