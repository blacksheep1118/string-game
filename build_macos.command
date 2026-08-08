#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")"
python3 -m pip install -r requirements-build.txt
python3 -m PyInstaller --noconfirm XianTu.spec
echo "Done: dist/XianTu"
