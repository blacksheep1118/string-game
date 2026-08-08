"""仙途游戏核心包。

入口脚本（``server.py``、``game.py`` 和 ``app.py``）只负责界面与启动，
剧情数据、游戏状态和选择结算统一从这里导入。
"""

from .engine import (
    ATTR_MIN,
    ATTR_NAMES,
    ATTR_TOTAL,
    TRAITS,
    Game,
    apply_character_setup,
    validate_attrs,
)
from .story import NODES, load_nodes

__all__ = [
    "ATTR_MIN",
    "ATTR_NAMES",
    "ATTR_TOTAL",
    "TRAITS",
    "Game",
    "NODES",
    "apply_character_setup",
    "load_nodes",
    "validate_attrs",
]
