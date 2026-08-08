"""项目路径与运行时数据目录配置。"""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
STATIC_DIR = PROJECT_ROOT / "static"


def story_file() -> Path:
    """返回剧情文件路径，允许测试或打包环境覆盖。"""

    configured = os.environ.get("XIANTU_STORY_FILE")
    return Path(configured).expanduser() if configured else DATA_DIR / "story_nodes.json"


def save_dir() -> Path:
    """返回玩家数据目录。

    默认仍使用项目下的 ``saves/`` 以兼容桌面版；发布或 CI 可通过
    ``XIANTU_SAVE_DIR`` 将玩家数据放到项目之外，避免误提交。
    """

    configured = os.environ.get("XIANTU_SAVE_DIR")
    return Path(configured).expanduser() if configured else PROJECT_ROOT / "saves"
