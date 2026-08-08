"""兼容入口：终端模式请运行 ``python game.py``。

实际规则和状态位于 ``xiantu/`` 包，剧情数据位于 ``data/story_nodes.json``。
保留这些导出是为了兼容旧存档工具、外部脚本和已有用户入口。
"""

from xiantu.engine import (
    ATTR_MIN,
    ATTR_NAMES,
    ATTR_TOTAL,
    TRAITS,
    Game,
    apply_character_setup,
    validate_attrs,
)
from xiantu.story import NODES, load_nodes
from xiantu.terminal import create_character, main
from xiantu.config import PROJECT_ROOT, save_dir

BASE_DIR = str(PROJECT_ROOT)
SAVE_DIR = str(save_dir())


if __name__ == "__main__":
    main()
