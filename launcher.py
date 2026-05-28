# -*- coding: utf-8 -*-
"""Cross-platform launcher for desktop, web, and terminal modes."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def run(args: list[str]) -> int:
    return subprocess.call(args, cwd=BASE_DIR)


def main() -> int:
    parser = argparse.ArgumentParser(description="仙途 · 文字修仙启动器")
    parser.add_argument("mode", nargs="?", choices=["desktop", "web", "terminal"], default="desktop")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default="5000")
    parser.add_argument("--lan", action="store_true", help="Web 模式监听局域网，方便手机访问")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    python = sys.executable
    if args.mode == "desktop":
        return run([python, os.path.join(BASE_DIR, "run_gui.pyw")])
    if args.mode == "terminal":
        return run([python, os.path.join(BASE_DIR, "game.py")])

    host = "0.0.0.0" if args.lan else args.host
    command = [python, os.path.join(BASE_DIR, "server.py"), "--host", host, "--port", str(args.port)]
    if args.no_browser:
        command.append("--no-browser")
    return run(command)


if __name__ == "__main__":
    raise SystemExit(main())
