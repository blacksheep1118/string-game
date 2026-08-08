"""终端界面：只处理输入输出，游戏规则由 ``xiantu.engine`` 提供。"""

from __future__ import annotations

import os
import json

from achievement_system import AchievementSystem
from playability import (
    BONUS_ENDING_TEXT,
    bonus_ending_available,
    check_achievements,
    choice_hints,
    daily_fortune,
    ensure_gameplay_state,
    get_goal,
    load_progression,
    mini_game_for,
    quick_restart_game,
    record_bonus_ending,
    read_progress_records,
    record_ending,
    resolve_mini_game,
    update_progression,
)
from save_manager import list_saves, load_save, save_game, validate_save_payload

from .config import DATA_DIR, save_dir
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
    _, fortune_bonus = daily_fortune()
    apply_character_setup(
        game,
        attrs,
        trait_key if trait_key in TRAITS else "1",
        fortune_bonus=fortune_bonus,
    )


def display_node(game: Game) -> bool:
    clear_screen()
    node = NODES[game.current_node]
    ensure_gameplay_state(game)
    print(f"\n{'═' * 52}\n  {node['title']}\n{'═' * 52}\n")
    print(f"  当前目标：{get_goal(node['title'])}\n")
    print("\n".join(f"  {line}" for line in node["text"].strip().splitlines()))
    choices = node.get("choices", [])
    if not choices:
        print("\n  1. 重新开始    2. 返回主菜单    3. 退出    4. 快速轮回")
        return True
    print()
    for index, choice in enumerate(choices, 1):
        hints = choice_hints(choice)
        suffix = f" 《{' · '.join(hints)}》" if hints else ""
        print(f"  [{index}] {choice['text']}{suffix}")
    print("\n  " + " | ".join(f"{name}:{game.attrs.get(name, 0)}" for name in ATTR_NAMES))
    print("  " + " | ".join(f"{name}:{game.resources.get(name, 0)}" for name in ("灵石", "历练", "丹药", "心魔", "轮回")))
    if game.artifacts:
        print("  法宝：" + "、".join(game.artifacts))
    if game.inventory:
        print("  丹药：" + "、".join(game.inventory))
    if game.affinity:
        print("  羁绊：" + "、".join(f"{name}:{value}" for name, value in game.affinity.items()))
    mini_game = mini_game_for(game.current_node, node, game)
    if mini_game and not mini_game.get("completed"):
        actions = "、".join(f"{item['id']}:{item['label']}" for item in mini_game.get("actions", []))
        print(f"  [m] 路线试炼：{actions}")
    return False


def show_progress() -> None:
    progression = load_progression(str(save_dir()))
    gallery = read_progress_records(str(save_dir()), "_gallery.json")
    achievements = AchievementSystem(str(DATA_DIR))
    achievements.load_unlocked(str(save_dir()))
    stats = achievements.get_stats()
    print("\n  ✦ 轮回进度 ✦")
    print(f"  结局：{len(gallery)} / {sum(1 for node in NODES.values() if not node.get('choices')) + 1}")
    print(f"  轮回点：{progression.get('legacy_points', 0)}")
    print(f"  成就：{stats['unlocked']} / {stats['total']} ({stats['progress']}%)")
    if gallery:
        print("  最近结局：" + "、".join(item.get("title", "") for item in gallery[-5:]))
    input("\n  按回车返回菜单…")


def run_game(game: Game) -> str:
    ending_seen = None
    while True:
        if display_node(game):
            if ending_seen != game.current_node:
                ending_seen = game.current_node
                settlement = record_ending(str(save_dir()), game, NODES)
                achievements = check_achievements(
                    str(save_dir()),
                    str(DATA_DIR),
                    game,
                    NODES,
                )
                summary = settlement["summary"]
                print(f"\n  结局已记录：{summary['rank']}级 · {summary['score']}分")
                for achievement in achievements:
                    print(f"  🏆 解锁成就：{achievement.get('name', '')}")
            if bonus_ending_available(str(save_dir()), NODES):
                print("  5. 解锁隐藏结局：天命所归")
            action = input("\n  请选择: ").strip()
            if action == "1":
                return "restart"
            if action == "2":
                return "menu"
            if action == "3":
                return "quit"
            if action == "4":
                game, legacy = quick_restart_game(game, str(save_dir()))
                ending_seen = None
                print(f"  已进入新轮回，幸运获得加成 +{legacy}。")
                input("  按回车继续…")
                continue
            if action == "5" and bonus_ending_available(str(save_dir()), NODES):
                try:
                    settlement = record_bonus_ending(str(save_dir()), game, NODES)
                except ValueError:
                    print("  隐藏结局暂时无法解锁。")
                else:
                    print("\n" + BONUS_ENDING_TEXT)
                    print(f"\n  隐藏结局已记录：{settlement['summary']['rank']}级 · {settlement['summary']['score']}分")
                input("\n  按回车返回菜单…")
                return "menu"
            continue

        raw = input("\n  选择编号（s 保存，m 试炼）: ").strip().lower()
        if raw == "s":
            filename, _ = save_game(str(save_dir()), game, NODES)
            update_progression(str(save_dir()), increments={"save_count": 1})
            achievements = check_achievements(
                str(save_dir()),
                str(DATA_DIR),
                game,
                NODES,
            )
            print(f"  已保存：{filename}")
            for achievement in achievements:
                print(f"  🏆 解锁成就：{achievement.get('name', '')}")
            continue
        if raw == "m":
            panel = mini_game_for(game.current_node, NODES[game.current_node], game)
            if not panel:
                print("  当前节点没有可执行的路线试炼。")
                input("  按回车继续…")
                continue
            if panel.get("completed"):
                print("  本轮试炼已经完成。")
                input("  按回车继续…")
                continue
            action = input(
                "  请输入试炼动作（"
                + ", ".join(item["id"] for item in panel.get("actions", []))
                + "): "
            ).strip().lower()
            try:
                feedback = resolve_mini_game(game, game.current_node, action)
            except ValueError:
                print("  试炼动作无效或已完成。")
                input("  按回车继续…")
                continue
            for message in feedback:
                print(f"  · {message}")
            for achievement in check_achievements(
                str(save_dir()),
                str(DATA_DIR),
                game,
                NODES,
            ):
                print(f"  🏆 解锁成就：{achievement.get('name', '')}")
            input("  按回车继续…")
            continue
        try:
            result = game.make_choice(int(raw) - 1)
        except (ValueError, KeyError):
            print("  选择无效。")
            continue
        for message in result.get("feedback", []):
            print(f"  · {message}")
        for achievement in check_achievements(
            str(save_dir()),
            str(DATA_DIR),
            game,
            NODES,
        ):
            print(f"  🏆 解锁成就：{achievement.get('name', '')}")
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
        choice = input("\n  请选择（p 查看轮回进度）: ").strip().lower()
        if choice == "p":
            show_progress()
            continue
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
                data = validate_save_payload(data, NODES, ATTR_NAMES)
            except (ValueError, IndexError, FileNotFoundError, OSError, json.JSONDecodeError):
                continue
            game = Game()
            game.load_data(data)
            if run_game(game) == "quit":
                return
        elif choice == "2" or (choice == "3" and files):
            return
