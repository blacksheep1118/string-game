"""终端界面：只处理输入输出，游戏规则由 ``xiantu.engine`` 提供。"""

from __future__ import annotations

import os

from playability import choice_hints, ensure_gameplay_state, get_goal
from save_manager import list_saves, load_save, save_game

from .config import save_dir
from .engine import ATTR_MIN, ATTR_NAMES, ATTR_TOTAL, Game, TRAITS, apply_character_setup
from .story import NODES


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def create_character(game: Game) -> None:
    attrs = {name: ATTR_MIN for name in ATTR_NAMES}
    remaining = ATTR_TOTAL - ATTR_MIN * len(ATTR_NAMES)
    while remaining > 0:
        clear_screen()
        print("\n  角色创建 · 分配属性\n")
        for name in ATTR_NAMES:
            print(f"  {name}: {attrs[name]}")
        print(f"\n  剩余点数: {remaining}")
        command = input("  输入“属性 点数”（如 根骨 10），或 q 完成: ").strip()
        if command.lower() == "q":
            break
        parts = command.split()
        if len(parts) != 2 or parts[0] not in attrs:
            print("  格式或属性名无效。")
            continue
        try:
            value = int(parts[1])
        except ValueError:
            print("  点数必须是整数。")
            continue
        if value < 0 or value > remaining:
            print("  点数超出可分配范围。")
            continue
        attrs[parts[0]] += value
        remaining -= value

    print("\n  选择初始词条:")
    for key, trait in TRAITS.items():
        print(f"  [{key}] {trait['name']} — {trait['desc']}")
    trait_key = input("  > ").strip()
    apply_character_setup(game, attrs, trait_key if trait_key in TRAITS else "1")


def display_node(game: Game) -> bool:
    clear_screen()
    node = NODES[game.current_node]
    ensure_gameplay_state(game)
    print(f"\n{'═' * 52}\n  {node['title']}\n{'═' * 52}\n")
    print(f"  当前目标：{get_goal(node['title'])}\n")
    print("\n".join(f"  {line}" for line in node["text"].strip().splitlines()))
    choices = node.get("choices", [])
    if not choices:
        print("\n  1. 重新开始    2. 返回主菜单    3. 退出")
        return True
    print()
    for index, choice in enumerate(choices, 1):
        hints = choice_hints(choice)
        suffix = f" 《{' · '.join(hints)}》" if hints else ""
        print(f"  [{index}] {choice['text']}{suffix}")
    print("\n  " + " | ".join(f"{name}:{game.attrs.get(name, 0)}" for name in ATTR_NAMES))
    print("  " + " | ".join(f"{name}:{game.resources.get(name, 0)}" for name in ("灵石", "历练", "丹药", "心魔", "轮回")))
    return False


def run_game(game: Game) -> str:
    while True:
        if display_node(game):
            action = input("\n  请选择: ").strip()
            if action == "1":
                game.current_node = "start"
                game.path_history = []
                game.reset_run_state()
                continue
            if action == "2":
                return "menu"
            if action == "3":
                return "quit"
            continue

        raw = input("\n  选择编号（s 保存）: ").strip().lower()
        if raw == "s":
            filename, _ = save_game(str(save_dir()), game, NODES)
            print(f"  已保存：{filename}")
            continue
        try:
            result = game.make_choice(int(raw) - 1)
        except (ValueError, KeyError):
            print("  选择无效。")
            continue
        for message in result.get("feedback", []):
            print(f"  · {message}")
        input("\n  按回车继续…")
    

def main() -> None:
    while True:
        clear_screen()
        files = list_saves(str(save_dir()))
        print("\n  ✦ 仙途 · 文字修仙 ✦\n")
        print("  1. 开始新游戏")
        if files:
            print("  2. 读取存档")
            print("  3. 退出")
        else:
            print("  2. 退出")
        choice = input("\n  请选择: ").strip()
        if choice == "1":
            game = Game()
            game.player_name = input("  角色名（回车为叶尘）: ").strip() or "叶尘"
            create_character(game)
            if run_game(game) == "quit":
                return
        elif choice == "2" and files:
            for index, item in enumerate(files, 1):
                print(f"  {index}. {item['name']} — {item['title']}")
            try:
                selected = int(input("  选择存档: ")) - 1
                data = load_save(str(save_dir()), files[selected]["filename"])
            except (ValueError, IndexError, FileNotFoundError):
                continue
            game = Game()
            game.load_data(data)
            if run_game(game) == "quit":
                return
        elif choice == "2" or (choice == "3" and files):
            return
