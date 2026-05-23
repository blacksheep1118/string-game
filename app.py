# -*- coding: utf-8 -*-
"""仙途 · 文字修仙 — 原生桌面版（tkinter，零额外依赖）"""
import json
import os
import sys
import random
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from game import Game, NODES, ATTR_NAMES, TRAITS, ATTR_TOTAL, ATTR_MIN

SAVE_DIR = "saves"

# ============================================================
# 字体回退 — 优先宋体，兼容所有系统
# ============================================================
FONT = ("SimSun", "Noto Serif CJK SC", "STSong", "NSimSun", "serif")


# ============================================================
# 配色方案 — 水墨风
# ============================================================
C = {
    "bg":        "#1a1410",
    "panel":     "#2a2218",
    "gold":      "#c9a96e",
    "gold_dim":  "#8a7040",
    "text":      "#d4c5a9",
    "text_dim":  "#7a6b55",
    "accent":    "#a0522d",
    "border":    "#3a3020",
    "btn_bg":    "#2a2218",
    "btn_hover": "#3a3020",
    "danger":    "#8b3a3a",
    "white":     "#e8dcc8",
}


class XianTuApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("仙途 · 文字修仙")
        # 恢复上次窗口位置/大小
        geo = self._load_geometry()
        self.root.geometry(geo)
        self.root.minsize(600, 480)
        self.root.configure(bg=C["bg"])

        self.game = Game()
        self.last_chapter = ""
        self.auto_save_file = ""
        self.undo_stack = []  # (current_node, path_history) tuples for undo

        # 持久化数据
        self.cleared_chapters = set()
        self.endings_count = 0
        self.achievements = set()
        self._load_persist()

        # 主题 & 字号
        self.theme = "dark"  # dark / light
        self.font_scale = 0  # -1 小 / 0 中 / 1 大

        # 速通计时
        self.timer_running = False
        self.timer_seconds = 0

        # 今日运势
        self.daily_fortune = random.choice(["大吉", "吉", "中吉", "小吉", "末吉"])
        self.fortune_bonus = {"大吉": 5, "吉": 3, "中吉": 1, "小吉": 0, "末吉": -3}[self.daily_fortune]

        # 窗口启动动画
        self.root.attributes("-alpha", 0.0)
        self._fade_in()

        # 关闭窗口确认
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # 背景音乐
        self.bgm_on = True
        self._start_bgm()

        self._setup_styles()
        self._build_ui()
        self._show_splash()
        self.root.after(1600, self.show_main_menu)

    def _load_persist(self):
        pf = os.path.join(SAVE_DIR, "_persist.json")
        if os.path.exists(pf):
            try:
                with open(pf, "r", encoding="utf-8") as f:
                    d = json.load(f)
                self.cleared_chapters = set(d.get("chapters", []))
                self.endings_count = d.get("endings_count", 0)
                self.achievements = set(d.get("achievements", []))
            except: pass

    def _save_persist(self):
        os.makedirs(SAVE_DIR, exist_ok=True)
        pf = os.path.join(SAVE_DIR, "_persist.json")
        with open(pf, "w", encoding="utf-8") as f:
            json.dump({
                "chapters": list(self.cleared_chapters),
                "endings_count": self.endings_count,
                "achievements": list(self.achievements),
            }, f)

    def _fade_in(self, step=0):
        alpha = step * 0.05
        if alpha < 1.0:
            self.root.attributes("-alpha", alpha)
            self.root.after(20, lambda: self._fade_in(step + 1))
        else:
            self.root.attributes("-alpha", 1.0)

    def _on_close(self):
        # 自动存档
        if self.game.current_node != "start" and self.game.path_history:
            self._do_save(overwrite=self.auto_save_file)
        # 保存窗口位置
        self._save_geometry()
        if messagebox.askyesno("退出游戏", "确定要退出吗？\n进度已自动保存。"):
            self.root.destroy()

    def _save_geometry(self):
        geo = self.root.geometry()
        pf = os.path.join(SAVE_DIR, "_persist.json")
        d = {}
        if os.path.exists(pf):
            try:
                with open(pf, "r", encoding="utf-8") as f:
                    d = json.load(f)
            except: pass
        d["geometry"] = geo
        with open(pf, "w", encoding="utf-8") as f:
            json.dump(d, f)

    def _load_geometry(self):
        pf = os.path.join(SAVE_DIR, "_persist.json")
        if os.path.exists(pf):
            try:
                with open(pf, "r", encoding="utf-8") as f:
                    d = json.load(f)
                return d.get("geometry", "880x680")
            except: pass
        return "880x680"

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=C["bg"])
        style.configure("TLabel", background=C["bg"], foreground=C["text"])
        style.configure("Title.TLabel", font=(*FONT, 24, "bold"), foreground=C["gold"], background=C["bg"])
        style.configure("Chapter.TLabel", font=(*FONT, 14), foreground=C["gold"], background=C["panel"])
        style.configure("Story.TLabel", font=(*FONT, 12), foreground=C["text"], background=C["panel"], wraplength=780)
        style.configure("AttrName.TLabel", font=(*FONT, 9), foreground=C["text_dim"], background=C["bg"])
        style.configure("AttrVal.TLabel", font=(*FONT, 9, "bold"), foreground=C["gold"], background=C["bg"])

    def _build_ui(self):
        # 顶部标题
        top = tk.Frame(self.root, bg=C["bg"])
        top.pack(fill="x", padx=20, pady=(20, 5))

        self.title_label = tk.Label(top, text="仙 途", font=(*FONT, 22, "bold"),
                                    fg=C["gold"], bg=C["bg"])
        self.title_label.pack()
        tk.Label(top, text="文 字 修 仙", font=(*FONT, 9),
                 fg=C["text_dim"], bg=C["bg"]).pack()

        # 分隔线
        sep = tk.Canvas(self.root, height=1, bg=C["bg"], highlightthickness=0)
        sep.create_line(30, 0, 850, 0, fill=C["border"])
        sep.pack(fill="x", padx=20)

        # 主内容区 — Canvas，鼠标滚轮滚动
        content_frame = tk.Frame(self.root, bg=C["bg"])
        content_frame.pack(fill="both", expand=True, padx=30, pady=5)

        self.content_canvas = tk.Canvas(content_frame, bg=C["panel"], highlightthickness=1,
                                        highlightbackground=C["border"])
        self.content_canvas.pack(fill="both", expand=True)

        self.content_inner = tk.Frame(self.content_canvas, bg=C["panel"])
        self.content_canvas.create_window((0, 0), window=self.content_inner, anchor="nw", tags="inner")

        def _on_configure(event):
            self.content_canvas.itemconfig("inner", width=event.width)
        self.content_canvas.bind("<Configure>", _on_configure)

        # 鼠标滚轮滚动
        def _on_mousewheel(event):
            self.content_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.content_canvas.bind("<MouseWheel>", _on_mousewheel)
        self.content_canvas.bind("<Enter>", lambda e: self.content_canvas.focus_set())

        # 属性面板 + 立绘
        self.attrs_frame = tk.Frame(self.root, bg=C["bg"])
        self.attrs_frame.pack(fill="x", padx=30, pady=(3, 0))
        self.portrait_label = tk.Label(self.attrs_frame, text="", font=(*FONT, 8),
                                        fg=C["text_dim"], bg=C["bg"], justify="left")

        # 底部按钮
        bottom = tk.Frame(self.root, bg=C["bg"])
        bottom.pack(fill="x", padx=30, pady=(0, 15))

        self._btn(bottom, "保存进度", self.save_game, C["text_dim"]).pack(side="left", padx=4)
        self._btn(bottom, "读取存档", self.show_load_dialog, C["text_dim"]).pack(side="left", padx=4)
        self._btn(bottom, "重新开始", self.restart_game, C["text_dim"]).pack(side="left", padx=4)
        self._btn(bottom, "结局画廊", self.show_gallery, C["text_dim"]).pack(side="left", padx=4)
        self._btn(bottom, "排行榜", self.show_leaderboard, C["text_dim"]).pack(side="left", padx=4)
        self.bgm_btn = self._btn(bottom, "🔊", self._toggle_bgm, C["text_dim"], font_size=8)
        self.bgm_btn.pack(side="right", padx=4)
        self._btn(bottom, "返回主菜单", self.show_main_menu, C["text_dim"]).pack(side="right", padx=4)

    def _btn(self, parent, text, cmd, color=C["text"], font_size=10):
        btn = tk.Button(parent, text=text, command=cmd,
                        font=(*FONT, font_size), fg=color, bg=C["btn_bg"],
                        activeforeground=C["gold"], activebackground=C["btn_hover"],
                        relief="flat", bd=1, padx=14, pady=4,
                        highlightbackground=C["border"], highlightthickness=1)
        btn.bind("<Enter>", lambda e, b=btn: b.configure(fg=C["gold"], bg=C["btn_hover"]))
        btn.bind("<Leave>", lambda e, b=btn: b.configure(fg=color, bg=C["btn_bg"]))
        return btn

    def _clear_content(self):
        for w in self.content_inner.winfo_children():
            w.destroy()
        # 清除属性栏
        for w in self.attrs_frame.winfo_children():
            w.destroy()

    def _render_attrs(self):
        for w in self.attrs_frame.winfo_children():
            w.destroy()
        if not self.game.attrs:
            return
        # 属性条
        max_val = 60
        bars_frame = tk.Frame(self.attrs_frame, bg=C["bg"])
        bars_frame.pack(side="left")
        for name in ATTR_NAMES:
            v = self.game.attrs.get(name, 0)
            pct = min(100, int(v / max_val * 100))
            f = tk.Frame(bars_frame, bg=C["bg"])
            f.pack(side="left", padx=6)
            tk.Label(f, text=f"{name} {v}", font=(*FONT, 9, "bold"),
                     fg=C["gold"], bg=C["bg"]).pack(side="left", padx=(0, 3))
            bar_canvas = tk.Canvas(f, width=50, height=5, bg=C["border"], highlightthickness=0)
            bar_canvas.pack(side="left")
            bar_canvas.create_rectangle(0, 0, pct / 100 * 50, 5, fill=C["gold"], outline="")
        # 立绘
        art = self._get_ascii_portrait()
        self.portrait_label = tk.Label(self.attrs_frame, text=art, font=(*FONT, 7),
                                        fg=C["text_dim"], bg=C["bg"], justify="left")
        self.portrait_label.pack(side="right", padx=(10, 0))

    def _auto_save(self, chapter):
        if chapter and chapter != self.last_chapter and self.last_chapter:
            self._do_save(overwrite=self.auto_save_file)
            if not self.auto_save_file:
                saves_dir = SAVE_DIR
                if os.path.exists(saves_dir):
                    files = sorted([f for f in os.listdir(saves_dir) if f.startswith("save_")], reverse=True)
                    if files:
                        self.auto_save_file = files[0]
        if chapter and chapter not in self.cleared_chapters:
            self.cleared_chapters.add(chapter)
            self._save_persist()
        if chapter:
            self.last_chapter = chapter

    def _get_chapter(self, title):
        import re
        m = re.match(r'^(第[〇一二三四五六七八九十终]+章)', title)
        return m.group(1) if m else ""

    def _do_save(self, overwrite=""):
        os.makedirs(SAVE_DIR, exist_ok=True)
        node = NODES.get(self.game.current_node, {})
        save_data = {
            "player_name": self.game.player_name,
            "current_node": self.game.current_node,
            "path_history": self.game.path_history,
            "attrs": self.game.attrs,
            "trait": self.game.trait,
            "title": node.get("title", ""),
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        if overwrite:
            filepath = os.path.join(SAVE_DIR, overwrite)
        else:
            filepath = os.path.join(SAVE_DIR, f"save_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        return os.path.basename(filepath)

    # ============================================================
    # 页面渲染
    # ============================================================
    def show_main_menu(self):
        self.last_chapter = ""
        self.auto_save_file = ""
        self._clear_content()
        self._render_attrs()
        self._clear_keys()

        tk.Label(self.content_inner, text="仙 途", font=(*FONT, 20, "bold"),
                 fg=C["gold"], bg=C["panel"]).pack(pady=(60, 5))
        tk.Label(self.content_inner, text="一段机缘，一个选择，一世仙途……",
                 font=(*FONT, 11), fg=C["text_dim"], bg=C["panel"]).pack(pady=(0, 30))
        tk.Label(self.content_inner, text="你的每一个决定，都将改变命运。",
                 font=(*FONT, 10), fg=C["text_dim"], bg=C["panel"]).pack(pady=(0, 30))

        menu_items = [
            ("1", "开始新游戏", self.show_new_game_name),
            ("2", "读取存档", self.show_load_dialog),
            ("3", "结局画廊", self.show_gallery),
            ("4", "排行榜", self.show_leaderboard),
            ("5", "设置", self.show_settings),
        ]
        if self.cleared_chapters:
            menu_items.append(("6", "章节选择", self.show_chapter_select))
        if self.endings_count >= 46:
            menu_items.append(("★", "隐藏结局", self._start_bonus_ending))

        for key, text, cmd in menu_items:
            self._big_choice(self.content_inner, key, text, cmd).pack(pady=4)

        for i, (key, _, cmd) in enumerate(menu_items):
            self.root.bind(key, lambda e, c=cmd: c())

        self._update_scroll()

    def _clear_keys(self):
        """清除所有按键绑定"""
        for k in list(self.root.bind()):
            self.root.unbind(k)

    def show_new_game_name(self):
        self._clear_content()
        self._render_attrs()
        self._clear_keys()

        tk.Label(self.content_inner, text="创建角色", font=(*FONT, 16, "bold"),
                 fg=C["gold"], bg=C["panel"]).pack(pady=(30, 15))
        tk.Label(self.content_inner, text="请输入你的角色名",
                 font=(*FONT, 11), fg=C["text"], bg=C["panel"]).pack()

        self.name_var = tk.StringVar(value="叶尘")
        entry = tk.Entry(self.content_inner, textvariable=self.name_var, font=(*FONT, 14),
                         fg=C["gold"], bg=C["btn_bg"], insertbackground=C["gold"],
                         relief="flat", bd=1, width=16, justify="center",
                         highlightbackground=C["border"], highlightthickness=1)
        entry.pack(pady=15)
        entry.focus_set()
        entry.bind("<Return>", lambda e: self.show_attr_allocation())
        entry.select_range(0, "end")

        self._big_choice(self.content_inner, "Enter", "确认", self.show_attr_allocation).pack(pady=10)
        self._update_scroll()

    def show_attr_allocation(self):
        name = self.name_var.get().strip() or "叶尘"
        self.game = Game()
        self.game.player_name = name

        self.attrs = {k: ATTR_MIN for k in ATTR_NAMES}
        self.remaining = ATTR_TOTAL - ATTR_MIN * len(ATTR_NAMES)

        hints = {"根骨": "战斗·肉身", "幸运": "机缘·寻宝", "魅力": "社交·交易", "精神": "意志·心魔", "悟性": "学习·功法"}

        self._clear_content()
        tk.Label(self.content_inner, text="分配属性", font=(*FONT, 16, "bold"),
                 fg=C["gold"], bg=C["panel"]).pack(pady=(30, 5))

        self.remain_label = tk.Label(self.content_inner,
                                     text=f"剩余点数: {self.remaining}",
                                     font=(*FONT, 12, "bold"), fg=C["gold"], bg=C["panel"])
        self.remain_label.pack(pady=(0, 15))

        self.attr_widgets = {}
        for k in ATTR_NAMES:
            row = tk.Frame(self.content_inner, bg=C["panel"])
            row.pack(pady=2)

            tk.Label(row, text=k, font=(*FONT, 11), fg=C["text"], bg=C["panel"], width=5, anchor="e").pack(side="left", padx=(0, 8))

            def make_minus(key=k):
                return lambda: self._adj_attr(key, -1)
            self._small_btn(row, "−", make_minus()).pack(side="left")

            val_label = tk.Label(row, text=str(ATTR_MIN), font=(*FONT, 12, "bold"),
                                 fg=C["gold"], bg=C["panel"], width=4)
            val_label.pack(side="left")
            self.attr_widgets[k] = val_label

            def make_plus(key=k):
                return lambda: self._adj_attr(key, 1)
            self._small_btn(row, "+", make_plus()).pack(side="left")

            # 进度条
            bar = tk.Canvas(row, width=120, height=6, bg=C["border"], highlightthickness=0)
            bar.pack(side="left", padx=(10, 5))
            self.attr_widgets[k + "_bar"] = bar

            tk.Label(row, text=hints[k], font=(*FONT, 9),
                     fg=C["text_dim"], bg=C["panel"]).pack(side="left")

        self._big_choice(self.content_inner, "Enter", "确认属性", self.show_trait_selection).pack(pady=20)

        # 键盘：↑↓ 选属性，← → 加减，Enter 确认
        attr_keys = list(ATTR_NAMES)
        self._attr_cursor = 0
        self._attr_highlight = None

        def update_highlight():
            if self._attr_highlight:
                self._attr_highlight.configure(bg=C["panel"])
            lbl = self.attr_widgets[attr_keys[self._attr_cursor]]
            lbl.configure(bg=C["btn_hover"])
            self._attr_highlight = lbl
        update_highlight()

        self.root.bind("<Up>", lambda e: self._nav_attr(-1, attr_keys))
        self.root.bind("<Down>", lambda e: self._nav_attr(1, attr_keys))
        self.root.bind("<Left>", lambda e: self._adj_attr(attr_keys[self._attr_cursor], -1))
        self.root.bind("<Right>", lambda e: self._adj_attr(attr_keys[self._attr_cursor], 1))
        self.root.bind("<Return>", lambda e: (
            self.show_trait_selection() if self._attr_cursor == len(attr_keys) - 1
            else self._nav_attr(1, attr_keys)
        ))

        self._update_scroll()

    def _nav_attr(self, delta, keys):
        self._attr_cursor = (self._attr_cursor + delta) % len(keys)
        if self._attr_highlight:
            self._attr_highlight.configure(bg=C["panel"])
        lbl = self.attr_widgets[keys[self._attr_cursor]]
        lbl.configure(bg=C["btn_hover"])
        self._attr_highlight = lbl

    def _adj_attr(self, key, delta):
        if delta > 0 and self.remaining <= 0:
            return
        if delta < 0 and self.attrs[key] <= ATTR_MIN:
            return
        self.attrs[key] += delta
        self.remaining -= delta

        self.attr_widgets[key].configure(text=str(self.attrs[key]))
        pct = min(100, self.attrs[key] / 40 * 100)
        bar = self.attr_widgets[key + "_bar"]
        bar.delete("all")
        bar.create_rectangle(0, 0, pct / 100 * 120, 6, fill=C["gold"], outline="")
        self.remain_label.configure(text=f"剩余点数: {self.remaining}")

    def show_trait_selection(self):
        if self.remaining > 0:
            if not messagebox.askyesno("确认", f"还有 {self.remaining} 点未分配，确定继续？"):
                return

        self.selected_trait = "1"

        self._clear_content()
        tk.Label(self.content_inner, text="选择词条", font=(*FONT, 16, "bold"),
                 fg=C["gold"], bg=C["panel"]).pack(pady=(30, 15))

        self.trait_btns = {}
        for k in sorted(TRAITS.keys(), key=int):
            t = TRAITS[k]
            bonus_str = "、".join(f"{a}+{b}" for a, b in t["bonus"].items())
            btn = tk.Button(self.content_inner,
                            text=f"{t['name']} — {bonus_str}\n{t['desc']}",
                            font=(*FONT, 10), fg=C["text"], bg=C["btn_bg"],
                            activeforeground=C["gold"], activebackground=C["btn_hover"],
                            relief="flat", bd=1, padx=16, pady=8, width=60, anchor="w",
                            justify="left", highlightbackground=C["border"], highlightthickness=1,
                            command=lambda key=k: self._select_trait(key))
            btn.pack(pady=3)
            self.trait_btns[k] = btn

        self._select_trait("1")
        self._big_choice(self.content_inner, "Enter", "开始游戏", self._start_game_with_extras).pack(pady=20)

        # 键盘：1-6 选词条，Enter 确认
        for k in sorted(TRAITS.keys(), key=int):
            self.root.bind(k, lambda e, key=k: self._select_trait(key))
        self.root.bind("<Return>", lambda e: self._start_game_with_extras())
        self.root.bind("<Escape>", lambda e: self.show_main_menu())

        self._update_scroll()

    def _select_trait(self, key):
        self.selected_trait = key
        for k, btn in self.trait_btns.items():
            if k == key:
                btn.configure(fg=C["gold"], bg=C["btn_hover"],
                              highlightbackground=C["gold"], highlightthickness=1)
            else:
                btn.configure(fg=C["text"], bg=C["btn_bg"],
                              highlightbackground=C["border"], highlightthickness=1)

    def _start_game(self):
        g = self.game
        trait_key = self.selected_trait
        if trait_key in TRAITS:
            g.trait = TRAITS[trait_key]["name"]
            for name, bonus in TRAITS[trait_key]["bonus"].items():
                self.attrs[name] = self.attrs.get(name, 0) + bonus
        g.attrs = self.attrs
        g.current_node = "start"
        g.path_history = []
        self.last_chapter = ""
        self.auto_save_file = ""
        self.render_current_node()

    def render_current_node(self):
        node = NODES.get(self.game.current_node)
        if not node:
            return

        chapter = self._get_chapter(node["title"])
        self._auto_save(chapter)

        self._clear_content()

        # 章节标题
        tk.Label(self.content_inner, text=f"—— {node['title']} ——",
                 font=(*FONT, 13, "bold"), fg=C["gold"], bg=C["panel"]).pack(pady=(25, 15))

        # 正文
        text_frame = tk.Frame(self.content_inner, bg=C["panel"])
        text_frame.pack(fill="x", padx=30)

        for line in node["text"].strip().split("\n"):
            tk.Label(text_frame, text=line, font=(*FONT, 11),
                     fg=C["text"], bg=C["panel"], anchor="w", justify="left",
                     wraplength=720).pack(anchor="w", pady=1)

        # 选项 / 结局
        self._clear_keys()

        choices = node.get("choices", [])
        if not choices:
            # 结局
            self._show_ending_summary(node)
            self.root.bind("1", lambda e: self.show_new_game_name())
            self.root.bind("2", lambda e: self.show_main_menu())
        else:
            tk.Frame(self.content_inner, bg=C["panel"], height=15).pack()
            # 获取原始 NODES 中的选项数据以显示效果提示
            node_data = NODES.get(self.game.current_node, {})
            raw_choices = node_data.get("choices", [])
            self._choice_callbacks = {}
            for i, c in enumerate(choices):
                idx = i
                cb = lambda n=idx: self._make_choice(n)
                self._choice_callbacks[i] = cb
                # 效果提示
                hint = ""
                if i < len(raw_choices):
                    eff = raw_choices[i].get("effect", {})
                    if eff:
                        parts = [f"+{v}{k}" for k, v in eff.items() if v > 0]
                        parts += [f"{v}{k}" for k, v in eff.items() if v < 0]
                        if parts:
                            hint = "  《" + " ".join(parts) + "》"
                self._big_choice(self.content_inner, str(i + 1), c["text"], cb, hint=hint
                                ).pack(pady=3, fill="x", padx=30)
            for i in range(len(choices)):
                key = str(i + 1)
                self.root.bind(key, lambda e, n=i: self._make_choice(n))
            # S 键存档
            self.root.bind("s", lambda e: self.save_game())
            self.root.bind("S", lambda e: self.save_game())
            # Esc 回主菜单
            self.root.bind("<Escape>", lambda e: self.show_main_menu())

            # 暗雷事件 — 5%概率触发
            if random.random() < 0.05:
                self._trigger_random_event()

            # 炼丹小游戏 — 特定节点
            if self.game.current_node in ("ch4_pill_power_1", "ch4_pill_power_3", "ch4_pill_heal_2"):
                self._pill_mini_game()

        self._render_attrs()
        self._update_scroll()

    def _show_ending_summary(self, node):
        tk.Frame(self.content_inner, bg=C["panel"], height=15).pack()

        # 停止计时
        self._stop_timer()

        # 记录结局
        self._record_ending()
        self._check_achievements()

        # 属性总结
        summary = tk.Frame(self.content_inner, bg=C["btn_bg"], highlightbackground=C["border"], highlightthickness=1)
        summary.pack(fill="x", padx=30, pady=10)

        tk.Label(summary, text="通关总结", font=(*FONT, 12, "bold"),
                 fg=C["gold"], bg=C["btn_bg"]).pack(pady=(10, 5))
        tk.Label(summary, text=f"词条: {self.game.trait}",
                 font=(*FONT, 10), fg=C["text_dim"], bg=C["btn_bg"]).pack()
        if self.timer_seconds > 0:
            mins, secs = divmod(self.timer_seconds, 60)
            tk.Label(summary, text=f"用时: {mins}分{secs}秒  运势: {self.daily_fortune}",
                     font=(*FONT, 9), fg=C["text_dim"], bg=C["btn_bg"]).pack()

        for k in ATTR_NAMES:
            v = self.game.attrs.get(k, 0)
            bar = "█" * min(20, v // 3) + "░" * max(0, 20 - v // 3)
            tk.Label(summary, text=f"  {k}: {v:>3}  {bar}",
                     font=(*FONT, 9), fg=C["text"], bg=C["btn_bg"]).pack(anchor="w", padx=40)

        tk.Frame(self.content_inner, bg=C["panel"], height=10).pack()

        self._big_choice(self.content_inner, "1", "重新开始", self.show_new_game_name).pack(pady=3, fill="x", padx=30)
        self._big_choice(self.content_inner, "2", "剧情回放", self._show_path_replay).pack(pady=3, fill="x", padx=30)
        self._big_choice(self.content_inner, "3", "返回主菜单", self.show_main_menu).pack(pady=3, fill="x", padx=30)
        self.root.bind("1", lambda e: self.show_new_game_name())
        self.root.bind("2", lambda e: self._show_path_replay())
        self.root.bind("3", lambda e: self.show_main_menu())

    def _record_ending(self):
        node = NODES.get(self.game.current_node, {})
        gallery_file = os.path.join(SAVE_DIR, "_gallery.json")
        gallery = []
        if os.path.exists(gallery_file):
            with open(gallery_file, "r", encoding="utf-8") as f:
                gallery = json.load(f)
        record = {
            "title": node.get("title", ""),
            "player_name": self.game.player_name,
            "trait": self.game.trait,
            "attrs": self.game.attrs,
            "path_count": len(self.game.path_history),
            "achieved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        existing = [e for e in gallery if e["title"] == node.get("title", "")]
        if not existing:
            gallery.append(record)
            with open(gallery_file, "w", encoding="utf-8") as f:
                json.dump(gallery, f, ensure_ascii=False, indent=2)

        # 排行榜记录
        self._save_leaderboard(node.get("title", ""))

        # 章节追踪
        for nid in self.game.path_history:
            ch = self._get_chapter(NODES.get(nid, {}).get("title", ""))
            if ch: self.cleared_chapters.add(ch)
        self.endings_count = len(gallery)
        self._save_persist()

    def _make_choice(self, idx):
        node = NODES.get(self.game.current_node)
        if not node:
            return
        choices = node.get("choices", [])
        if idx >= len(choices):
            return

        # 保存撤销点
        self.undo_stack.append((self.game.current_node, list(self.game.path_history)))

        choice = choices[idx]
        self.game.path_history.append(self.game.current_node)

        # 属性加成
        effect = choice.get("effect", {})
        for attr, delta in effect.items():
            if attr in self.game.attrs:
                self.game.attrs[attr] += delta

        # 属性判定
        req = choice.get("require", {})
        if req:
            met = all(self.game.attrs.get(k, 0) >= v for k, v in req.items())
            if not met and "fail" in choice:
                self.game.current_node = choice["fail"]
                self.render_current_node()
                return

        self.game.current_node = choice.get("next", self.game.current_node)
        self._inject_gameplay_rewards()
        self._check_achievements()
        self.render_current_node()

    # ============================================================
    # 存档 / 画廊
    # ============================================================
    def save_game(self):
        filename = self._do_save()
        self._toast(f"已保存: {filename}")

    def show_load_dialog(self):
        os.makedirs(SAVE_DIR, exist_ok=True)
        saves = []
        for f in sorted(os.listdir(SAVE_DIR), reverse=True):
            if f.endswith(".json") and not f.startswith("_"):
                filepath = os.path.join(SAVE_DIR, f)
                try:
                    with open(filepath, "r", encoding="utf-8") as fp:
                        d = json.load(fp)
                    saves.append({
                        "filename": f,
                        "name": d.get("player_name", "未知"),
                        "title": d.get("title", "未知"),
                        "saved_at": d.get("saved_at", "未知"),
                    })
                except (json.JSONDecodeError, KeyError):
                    pass

        self._clear_content()
        tk.Label(self.content_inner, text="读取存档", font=(*FONT, 16, "bold"),
                 fg=C["gold"], bg=C["panel"]).pack(pady=(30, 15))

        if not saves:
            tk.Label(self.content_inner, text="暂无存档", font=(*FONT, 11),
                     fg=C["text_dim"], bg=C["panel"]).pack(pady=20)
        else:
            for s in saves:
                row = tk.Frame(self.content_inner, bg=C["panel"])
                row.pack(fill="x", padx=30, pady=2)

                load_btn = tk.Button(row, text=f"{s['name']} — {s['title']}\n{s['saved_at']}",
                                     font=(*FONT, 10), fg=C["text"], bg=C["btn_bg"],
                                     activeforeground=C["gold"], activebackground=C["btn_hover"],
                                     relief="flat", bd=1, padx=12, pady=6, anchor="w", justify="left",
                                     highlightbackground=C["border"], highlightthickness=1,
                                     command=lambda f=s['filename']: self._load_game(f))
                load_btn.pack(side="left", fill="x", expand=True)

                del_btn = tk.Button(row, text="✕", font=(*FONT, 10),
                                    fg=C["danger"], bg=C["btn_bg"],
                                    activeforeground="red", activebackground=C["btn_hover"],
                                    relief="flat", bd=1, padx=8, pady=6,
                                    highlightbackground=C["border"], highlightthickness=1,
                                    command=lambda f=s['filename']: self._delete_save(f))
                del_btn.pack(side="right", padx=(4, 0))

        self._big_choice(self.content_inner, "Esc", "返回主菜单", self.show_main_menu).pack(pady=15)

        # 键盘：1-N 选存档，D 删除，Esc 返回
        for i, s in enumerate(saves[:9]):
            self.root.bind(str(i + 1), lambda e, f=s['filename']: self._load_game(f))
        self.root.bind("<Escape>", lambda e: self.show_main_menu())

        self._update_scroll()

    def _load_game(self, filename):
        filepath = os.path.join(SAVE_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            d = json.load(f)
        self.game = Game()
        self.game.player_name = d.get("player_name", "叶尘")
        self.game.current_node = d.get("current_node", "start")
        self.game.path_history = d.get("path_history", [])
        self.game.attrs = d.get("attrs", {k: 20 for k in ATTR_NAMES})
        self.game.trait = d.get("trait", "")
        self.last_chapter = ""
        self.auto_save_file = ""
        self.render_current_node()

    def _delete_save(self, filename):
        if messagebox.askyesno("删除存档", f"确定删除这个存档吗？\n此操作不可恢复。"):
            os.remove(os.path.join(SAVE_DIR, filename))
            self.show_load_dialog()

    def restart_game(self):
        if messagebox.askyesno("重新开始", "确定重新开始吗？当前进度将丢失。"):
            self.show_new_game_name()

    def show_gallery(self):
        gallery_file = os.path.join(SAVE_DIR, "_gallery.json")
        gallery = []
        if os.path.exists(gallery_file):
            with open(gallery_file, "r", encoding="utf-8") as f:
                gallery = json.load(f)

        self._clear_content()
        tk.Label(self.content_inner, text="结局画廊", font=(*FONT, 16, "bold"),
                 fg=C["gold"], bg=C["panel"]).pack(pady=(30, 5))
        tk.Label(self.content_inner, text=f"已收集: {len(gallery)} / 46",
                 font=(*FONT, 10), fg=C["text_dim"], bg=C["panel"]).pack(pady=(0, 15))

        if not gallery:
            tk.Label(self.content_inner, text="还没有达成任何结局，去探索吧。",
                     font=(*FONT, 11), fg=C["text_dim"], bg=C["panel"]).pack(pady=20)
        else:
            grid = tk.Frame(self.content_inner, bg=C["panel"])
            grid.pack(pady=5)

            rank_colors = {"SS": C["gold"], "S": C["accent"], "A": "#6b8e6b", "B": "#3a5070", "C": "#5a3a3a", "D": "#5a3a3a"}
            for i, e in enumerate(gallery):
                raw_title = e.get("title", "")
                title = raw_title.replace("【结局】", "")
                # 取结局名的第一个字作为图标
                icon = title[0] if title else "?"
                # 提取评价
                rank = "?"
                for r in ["SS", "S——", "S：", "A——", "A：", "B——", "B：", "C——", "C：", "D——", "D："]:
                    if r.rstrip("——：") in raw_title[:30]:
                        rank = r[0] if len(r) == 1 else r[0]
                        break
                rcolor = rank_colors.get(rank, C["text_dim"])

                card = tk.Frame(grid, bg=C["btn_bg"], highlightbackground=C["border"], highlightthickness=1)
                card.grid(row=i // 4, column=i % 4, padx=4, pady=4, sticky="nsew")

                # 大图标
                tk.Label(card, text=icon, font=(*FONT, 36, "bold"),
                         fg=rcolor, bg=C["btn_bg"]).pack(pady=(12, 0))
                # 评价角标
                tk.Label(card, text=rank, font=(*FONT, 8, "bold"),
                         fg=C["bg"], bg=rcolor, padx=6).pack(pady=(2, 6))
                tk.Label(card, text=title, font=(*FONT, 9),
                         fg=C["text"], bg=C["btn_bg"], wraplength=140).pack(padx=8)
                tk.Label(card, text=f"{e.get('player_name','')} · {e.get('trait','')}",
                         font=(*FONT, 7), fg=C["text_dim"], bg=C["btn_bg"]).pack(pady=(2, 8))

            for i in range(4):
                grid.columnconfigure(i, weight=1)

        self._big_choice(self.content_inner, "Esc", "返回主菜单", self.show_main_menu).pack(pady=15)
        self.root.bind("<Escape>", lambda e: self.show_main_menu())
        self._update_scroll()

    # ============================================================
    # 辅助
    # ============================================================
    def _big_choice(self, parent, idx_str, text, cmd, hint=""):
        display = f"  [{idx_str}]  {text}"
        if hint:
            display += f"  {hint}"
        btn = tk.Button(parent, text=display,
                        font=(*FONT, 11), fg=C["text"], bg=C["btn_bg"],
                        activeforeground=C["gold"], activebackground=C["btn_hover"],
                        relief="flat", bd=1, padx=16, pady=10, anchor="w",
                        highlightbackground=C["border"], highlightthickness=1,
                        command=cmd)
        btn.bind("<Enter>", lambda e, b=btn: b.configure(fg=C["gold"], bg=C["btn_hover"],
                                                          highlightbackground=C["gold"]))
        btn.bind("<Leave>", lambda e, b=btn: b.configure(fg=C["text"], bg=C["btn_bg"],
                                                          highlightbackground=C["border"]))
        return btn

    def _small_btn(self, parent, text, cmd):
        btn = tk.Button(parent, text=text, font=(*FONT, 10, "bold"),
                        fg=C["text"], bg=C["btn_bg"],
                        activeforeground=C["gold"], activebackground=C["btn_hover"],
                        relief="flat", bd=1, padx=6, pady=1,
                        highlightbackground=C["border"], highlightthickness=1,
                        command=cmd)
        return btn

    def _toast(self, msg):
        toast = tk.Toplevel(self.root)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        tk.Label(toast, text=msg, font=(*FONT, 10), fg=C["gold"], bg=C["panel"],
                 relief="solid", bd=1, padx=20, pady=8,
                 highlightbackground=C["gold"], highlightthickness=1).pack()

        # 居中
        self.root.update_idletasks()
        rx, ry = self.root.winfo_rootx(), self.root.winfo_rooty()
        rw, rh = self.root.winfo_width(), self.root.winfo_height()
        tw = toast.winfo_reqwidth()
        toast.geometry(f"+{rx + (rw - tw) // 2}+{ry + 20}")

        toast.after(2000, toast.destroy)

    def _update_scroll(self):
        self.content_inner.update_idletasks()
        self.content_canvas.configure(scrollregion=self.content_canvas.bbox("all"))
        # 自动滚回顶部
        self.content_canvas.yview_moveto(0)

    # ============================================================
    # 1. 暗雷事件系统
    # ============================================================
    def _trigger_random_event(self):
        luck = self.game.attrs.get("幸运", 20)
        events = [
            ("路边遗宝", "你在一棵古树下发现了一个破旧的包裹……", {"幸运": 3, "悟性": 1}),
            ("妖兽夜袭", "夜晚营地被一头落单妖兽突袭！你持剑迎战……", {"根骨": 2}),
            ("山洞奇遇", "避雨时误入一个山洞，壁上刻着残缺的古功法……", {"悟性": 3}),
            ("老人赠书", "一位路过的老修士见你顺眼，赠你一本心得笔记。", {"悟性": 2, "精神": 1}),
            ("灵泉沐浴", "你发现了一处隐秘的灵泉，沐浴后神清气爽。", {"根骨": 2, "精神": 2}),
            ("黑市偶遇", "误入地下黑市，见识了修仙界的另一面。", {"魅力": 2, "幸运": 1}),
            ("天降陨铁", "一颗流星坠落在不远处，竟是一块天外陨铁！", {"幸运": 3, "根骨": 1}),
            ("迷路困境", "在山中迷路三天，但也因此磨练了意志。", {"精神": 3}),
        ]
        probs = [max(10, luck - i * 5) for i in range(len(events))]
        total = sum(probs)
        r = random.randint(1, total)
        cum = 0
        chosen = events[0]
        for evt, p in zip(events, probs):
            cum += p
            if r <= cum:
                chosen = evt
                break

        name, desc, effects = chosen
        msg = f"【随机事件】{name}\n\n{desc}\n\n"
        for k, v in effects.items():
            self.game.attrs[k] = self.game.attrs.get(k, 0) + v
            sign = "+" if v > 0 else ""
            msg += f"  {k} {sign}{v}\n"

        messagebox.showinfo("机缘降临", msg)
        self._render_attrs()

    # ============================================================
    # 2. 全结局彩蛋 — SS+ 隐藏结局
    # ============================================================
    def _start_bonus_ending(self):
        self.game = Game()
        self.game.player_name = "天命者"
        self.game.trait = "万法归一"
        self.game.attrs = {k: 99 for k in ATTR_NAMES}
        self.game.path_history = []
        self.last_chapter = ""
        self.auto_save_file = ""

        self._clear_content()
        tk.Label(self.content_inner, text="—— 隐藏结局：天命所归 ——",
                 font=(*FONT, 14, "bold"), fg=C["gold"], bg=C["panel"]).pack(pady=(30, 15))
        text = (
            "你已踏遍仙途的每一个角落，见证了所有的命运分支。\n\n"
            "四十六种结局在你心中汇聚成河——\n"
            "你终于明白，仙途不是一条路，而是万千可能性的总和。\n\n"
            "天道有常，众生皆苦。\n"
            "而你，已超脱其中。\n\n"
            "═══════════════════\n"
            "  🏆 达成隐藏结局：天命所归\n"
            "  评价：SS+ —— 你已洞悉一切\n"
            "═══════════════════"
        )
        tk.Label(self.content_inner, text=text, font=(*FONT, 11),
                 fg=C["text"], bg=C["panel"], justify="left",
                 wraplength=700).pack(padx=30, pady=10)

        tk.Frame(self.content_inner, bg=C["panel"], height=15).pack()
        self._big_choice(self.content_inner, "1", "返回主菜单", self.show_main_menu).pack(pady=3, fill="x", padx=30)
        self.root.bind("1", lambda e: self.show_main_menu())
        self._render_attrs()
        self._update_scroll()

        # 记录
        node = {"title": "【隐藏结局】天命所归  评价：SS+——你已洞悉一切"}
        gallery_file = os.path.join(SAVE_DIR, "_gallery.json")
        gallery = []
        if os.path.exists(gallery_file):
            with open(gallery_file, "r", encoding="utf-8") as f:
                gallery = json.load(f)
        if not any(e.get("title","") == node["title"] for e in gallery):
            gallery.append({"title": node["title"], "player_name": "天命者", "trait": "万法归一",
                           "attrs": self.game.attrs, "path_count": 0,
                           "achieved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
            with open(gallery_file, "w", encoding="utf-8") as f:
                json.dump(gallery, f, ensure_ascii=False, indent=2)

    # ============================================================
    # 4. 章节选择
    # ============================================================
    def show_chapter_select(self):
        chapters = sorted(self.cleared_chapters, key=lambda x: (
            "〇一二三四五六七八九终".index(x[1]) if x[1] in "〇一二三四五六七八九终" else 99))
        self._clear_content()
        tk.Label(self.content_inner, text="章节选择", font=(*FONT, 16, "bold"),
                 fg=C["gold"], bg=C["panel"]).pack(pady=(30, 15))

        if not chapters:
            tk.Label(self.content_inner, text="暂无已通关章节，先完成一次游戏吧。",
                     font=(*FONT, 11), fg=C["text_dim"], bg=C["panel"]).pack(pady=20)
        else:
            for ch in chapters:
                # 找该章节第一个节点
                for nid, nd in NODES.items():
                    if self._get_chapter(nd.get("title", "")) == ch and nd.get("choices"):
                        self._big_choice(self.content_inner, "→", f"从 {ch} 开始",
                                        lambda n=nid: self._jump_chapter(n)
                                        ).pack(pady=3, fill="x", padx=30)
                        break

        self._big_choice(self.content_inner, "Esc", "返回主菜单", self.show_main_menu).pack(pady=15)
        self.root.bind("<Escape>", lambda e: self.show_main_menu())
        self._update_scroll()

    def _jump_chapter(self, node_id):
        self.game = Game()
        self.game.player_name = "轮回者"
        self.game.attrs = {k: 25 for k in ATTR_NAMES}
        self.game.trait = "轮回印记"
        self.game.current_node = node_id
        self.game.path_history = ["start"]
        self.last_chapter = ""
        self.auto_save_file = ""
        self.render_current_node()

    # ============================================================
    # 5. 背景音乐
    # ============================================================
    def _start_bgm(self):
        def loop():
            notes = [262, 294, 330, 349, 392, 349, 330, 294,  # 古风音阶
                     330, 392, 440, 523, 440, 392, 330, 294]
            durations = [0.6, 0.4, 0.6, 0.4, 0.8, 0.4, 0.6, 0.4,
                         0.6, 0.4, 0.6, 0.8, 0.4, 0.6, 0.4, 0.8]
            i = 0
            while getattr(self, "bgm_on", True):
                try:
                    import winsound
                    winsound.Beep(notes[i % len(notes)], int(durations[i % len(durations)] * 800))
                    i += 1
                    time.sleep(0.3)
                except:
                    break
        t = threading.Thread(target=loop, daemon=True)
        t.start()

    def _toggle_bgm(self):
        self.bgm_on = not self.bgm_on
        self.bgm_btn.configure(text="🔊" if self.bgm_on else "🔇")

    # ============================================================
    # 7. 炼丹小游戏
    # ============================================================
    def _pill_mini_game(self):
         if not messagebox.askyesno("炼丹", "炼丹炉火候需要调控。\n按确认开始控火……"):
             return
         result = messagebox.askquestion("控火", "火势渐旺！\n—— 减小火力？ ——",
                                        icon="question")
         if result == "yes":
             result2 = messagebox.askquestion("控火", "火势偏小……\n—— 加大火力？ ——",
                                             icon="question")
             if result2 == "yes":
                 # 完美控火
                 self.game.attrs["悟性"] = self.game.attrs.get("悟性", 0) + 3
                 messagebox.showinfo("炼丹成功", "火候掌控完美！丹药品质上乘。\n悟性 +3")
             else:
                 self.game.attrs["悟性"] = self.game.attrs.get("悟性", 0) + 1
                 messagebox.showinfo("炼丹完成", "丹药炼成，品质尚可。\n悟性 +1")
         else:
             result2 = messagebox.askquestion("控火", "火力过猛，丹炉震动！\n—— 紧急降温？ ——",
                                             icon="warning")
             if result2 == "yes":
                 self.game.attrs["精神"] = self.game.attrs.get("精神", 0) + 2
                 messagebox.showinfo("化险为夷", "及时降温，丹药保住了。\n精神 +2")
             else:
                 messagebox.showinfo("炸炉", "丹炉爆炸……但你在爆炸中悟到了一些东西。")

    # ============================================================
    # 8. 角色立绘
    # ============================================================
    def _get_ascii_portrait(self):
        total = sum(self.game.attrs.values()) if self.game.attrs else 100
        if total >= 300:
            return ("  ⚔ 元婴真君 ⚔\n"
                    "    ╱╲ ╱╲\n"
                    "   ╱  ◉  ╲\n"
                    "  ╱   ╱╲   ╲\n"
                    " ╱   ╱  ╲   ╲\n"
                    "╱▔▔▔╲╱▔▔╲▔▔▔╲")
        elif total >= 200:
            return ("  ✦ 金丹修士 ✦\n"
                    "    ╱◉◉╲\n"
                    "   ╱ ╱╲ ╲\n"
                    "  ╱ ╱  ╲ ╲\n"
                    "  ▔▔▔▔▔▔▔▔▔")
        elif total >= 150:
            return ("  ◆ 筑基修士 ◆\n"
                    "    ╭─◉─╮\n"
                    "    │ ╱╲ │\n"
                    "    ╰─╯╰─╯")
        elif total >= 100:
            return ("  ▪ 炼气修士 ▪\n"
                    "    ╭───╮\n"
                    "    │ ◉ │\n"
                    "    ╰───╯")
        return ""

    # ============================================================
    # 9. 排行榜
    # ============================================================
    def _save_leaderboard(self, ending_title):
        lb_file = os.path.join(SAVE_DIR, "_leaderboard.json")
        lb = []
        if os.path.exists(lb_file):
            with open(lb_file, "r", encoding="utf-8") as f:
                lb = json.load(f)

        score = sum(self.game.attrs.values())
        # 提取评价
        rank = "?"
        for r in ["SS", "S", "A", "B", "C", "D"]:
            if r in ending_title[:30]:
                rank = r
                break
        rank_mult = {"SS": 300, "S": 200, "A": 150, "B": 100, "C": 50, "D": 30}.get(rank, 50)
        total_score = score + rank_mult + len(self.game.path_history)

        lb.append({
            "player": self.game.player_name,
            "ending": ending_title.replace("【结局】", ""),
            "rank": rank,
            "score": total_score,
            "attrs_total": score,
            "decisions": len(self.game.path_history),
            "date": datetime.now().strftime("%m-%d %H:%M"),
        })
        lb.sort(key=lambda x: x["score"], reverse=True)
        lb = lb[:50]  # 保留前50
        with open(lb_file, "w", encoding="utf-8") as f:
            json.dump(lb, f, ensure_ascii=False, indent=2)

    def show_leaderboard(self):
        lb_file = os.path.join(SAVE_DIR, "_leaderboard.json")
        lb = []
        if os.path.exists(lb_file):
            with open(lb_file, "r", encoding="utf-8") as f:
                lb = json.load(f)

        self._clear_content()
        tk.Label(self.content_inner, text="排行榜", font=(*FONT, 16, "bold"),
                 fg=C["gold"], bg=C["panel"]).pack(pady=(30, 5))

        if not lb:
            tk.Label(self.content_inner, text="暂无记录，完成一次游戏后上榜。",
                     font=(*FONT, 11), fg=C["text_dim"], bg=C["panel"]).pack(pady=20)
        else:
            # 表头
            hdr = tk.Frame(self.content_inner, bg=C["btn_bg"])
            hdr.pack(fill="x", padx=20, pady=(10, 0))
            for t, w in [("#", 3), ("玩家", 12), ("结局", 18), ("评分", 5), ("总分", 6), ("日期", 10)]:
                tk.Label(hdr, text=t, font=(*FONT, 9, "bold"), fg=C["gold"],
                         bg=C["btn_bg"], width=w, anchor="w").pack(side="left")

            for i, entry in enumerate(lb):
                row = tk.Frame(self.content_inner, bg=C["panel" if i % 2 == 0 else "btn_bg"])
                row.pack(fill="x", padx=20)
                vals = [str(i + 1), entry.get("player", "")[:6],
                        entry.get("ending", "")[:12],
                        entry.get("rank", "?"),
                        str(entry.get("score", 0)),
                        entry.get("date", "")]
                widths = [3, 12, 18, 5, 6, 10]
                for v, w in zip(vals, widths):
                    tk.Label(row, text=v, font=(*FONT, 9), fg=C["text"],
                             bg=row["bg"], width=w, anchor="w").pack(side="left")

        self._big_choice(self.content_inner, "Esc", "返回主菜单", self.show_main_menu).pack(pady=15)
        self.root.bind("<Escape>", lambda e: self.show_main_menu())
        self._update_scroll()

    # ============================================================
    # 10. 剧情回放
    # ============================================================
    def _show_path_replay(self):
        self._clear_content()
        tk.Label(self.content_inner, text="剧情回放", font=(*FONT, 16, "bold"),
                 fg=C["gold"], bg=C["panel"]).pack(pady=(30, 10))
        tk.Label(self.content_inner, text=f"{self.game.player_name} · {self.game.trait}",
                 font=(*FONT, 10), fg=C["text_dim"], bg=C["panel"]).pack()

        path_frame = tk.Frame(self.content_inner, bg=C["panel"])
        path_frame.pack(fill="x", padx=20, pady=10)

        for i, nid in enumerate(self.game.path_history):
            node = NODES.get(nid, {})
            title = node.get("title", nid)
            # 属性快照（简化：用最后属性）
            row = tk.Frame(path_frame, bg=C["panel" if i % 2 == 0 else "btn_bg"])
            row.pack(fill="x", pady=1)
            tk.Label(row, text=f"  {i+1}.", font=(*FONT, 8), fg=C["text_dim"],
                     bg=row["bg"], width=3).pack(side="left")
            tk.Label(row, text=title, font=(*FONT, 9), fg=C["text"],
                     bg=row["bg"], anchor="w").pack(side="left", fill="x", expand=True)

        # 结局
        end_node = NODES.get(self.game.current_node, {})
        row = tk.Frame(path_frame, bg=C["btn_bg"])
        row.pack(fill="x", pady=1)
        tk.Label(row, text="  ★", font=(*FONT, 8), fg=C["gold"],
                 bg=row["bg"], width=3).pack(side="left")
        tk.Label(row, text=end_node.get("title", "结局"), font=(*FONT, 9, "bold"),
                 fg=C["gold"], bg=row["bg"], anchor="w").pack(side="left", fill="x", expand=True)

        self._big_choice(self.content_inner, "1", "重新开始", self.show_new_game_name).pack(pady=3, fill="x", padx=30)
        self._big_choice(self.content_inner, "Esc", "返回主菜单", self.show_main_menu).pack(pady=3, fill="x", padx=30)
        self.root.bind("1", lambda e: self.show_new_game_name())
        self.root.bind("<Escape>", lambda e: self.show_main_menu())
        self._update_scroll()

    # ============================================================
    # 主题切换 & 字号
    # ============================================================
    def _apply_theme(self):
        if self.theme == "light":
            C.update({"bg": "#f5f0e8", "panel": "#faf6ef", "text": "#3a3020",
                       "text_dim": "#8a7b65", "btn_bg": "#f0ead8", "btn_hover": "#e8e0c8",
                       "border": "#c8b898", "gold": "#8a6020", "gold_dim": "#a08050"})
        else:
            C.update({"bg": "#1a1410", "panel": "#2a2218", "text": "#d4c5a9",
                       "text_dim": "#7a6b55", "btn_bg": "#2a2218", "btn_hover": "#3a3020",
                       "border": "#3a3020", "gold": "#c9a96e", "gold_dim": "#8a7040"})
        self.root.configure(bg=C["bg"])

    def _toggle_theme(self):
        self.theme = "light" if self.theme == "dark" else "dark"
        self._apply_theme()
        self.show_main_menu()

    def _cycle_font_size(self):
        self.font_scale = (self.font_scale + 1) % 3  # -1, 0, 1
        sizes = {-1: "小", 0: "中", 1: "大"}
        self._toast(f"字号: {sizes[self.font_scale]}")
        self.show_main_menu()

    def _sized_font(self, base_size):
        return (*FONT, base_size + self.font_scale * 2)

    # ============================================================
    # 打字机效果
    # ============================================================
    def _typewriter_show(self, text, callback, container=None):
        """逐字显示文本，完成后调用 callback"""
        if container is None:
            container = self.content_inner
        label = tk.Label(container, text="", font=self._sized_font(11),
                         fg=C["text"], bg=C["panel"], anchor="w", justify="left",
                         wraplength=720)
        label.pack(anchor="w", pady=1)

        lines = text.strip().split("\n")
        all_chars = []
        for line in lines:
            all_chars.extend(list(line))
            all_chars.append("\n")

        def reveal(idx=0):
            if idx < len(all_chars):
                current = label.cget("text") + all_chars[idx]
                label.configure(text=current)
                self.root.after(25, lambda: reveal(idx + 1))
            elif callback:
                callback()
        reveal()

    # ============================================================
    # 回合制战斗
    # ============================================================
    def _initiate_combat(self, enemy_name, enemy_hp, on_win, on_lose):
        self.game.combat_stats = {"hp": 100, "max_hp": 100}
        dialog = tk.Toplevel(self.root)
        dialog.title("战斗")
        dialog.geometry("400x350")
        dialog.configure(bg=C["panel"])
        dialog.transient(self.root)
        dialog.grab_set()

        enemy = {"name": enemy_name, "hp": enemy_hp, "max_hp": enemy_hp}

        def update_ui():
            for w in frame.winfo_children(): w.destroy()
            tk.Label(frame, text=f"⚔ {enemy['name']}", font=self._sized_font(13, "bold"),
                     fg=C["danger"], bg=C["panel"]).pack(pady=5)
            tk.Label(frame, text=f"敌人 HP: {'█' * max(0, enemy['hp'] // 5)}{'░' * max(0, (enemy['max_hp'] - enemy['hp']) // 5)}",
                     font=self._sized_font(10), fg=C["text"], bg=C["panel"]).pack()
            tk.Label(frame, text=f"你的 HP: {self.game.combat_stats['hp']}/{self.game.combat_stats['max_hp']}",
                     font=self._sized_font(10), fg=C["gold"], bg=C["panel"]).pack(pady=(5, 15))

        frame = tk.Frame(dialog, bg=C["panel"])
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        update_ui()

        def player_attack():
            dmg = random.randint(15, 30) + self.game.attrs.get("根骨", 20) // 5
            enemy["hp"] -= dmg
            if enemy["hp"] <= 0:
                dialog.destroy()
                self.game.combat_stats["max_hp"] += 10
                self.game.affinity["战斗经验"] = self.game.affinity.get("战斗经验", 0) + 1
                on_win()
                return
            # 敌人反击
            edmg = random.randint(10, 25)
            self.game.combat_stats["hp"] -= edmg
            if self.game.combat_stats["hp"] <= 0:
                dialog.destroy()
                on_lose()
                return
            update_ui()

        def player_defend():
            edmg = max(0, random.randint(10, 25) - self.game.attrs.get("精神", 20) // 4)
            self.game.combat_stats["hp"] -= edmg
            if self.game.combat_stats["hp"] <= 0:
                dialog.destroy()
                on_lose()
                return
            update_ui()

        btn_frame = tk.Frame(dialog, bg=C["panel"])
        btn_frame.pack(pady=10)
        self._btn(btn_frame, "[1] 攻击", player_attack).pack(side="left", padx=5)
        self._btn(btn_frame, "[2] 防御", player_defend).pack(side="left", padx=5)
        dialog.bind("1", lambda e: player_attack())
        dialog.bind("2", lambda e: player_defend())

    # ============================================================
    # 法宝 / 丹药 / 好感度 渲染
    # ============================================================
    def _render_extras(self, container):
        """在属性面板下方显示法宝/丹药/好感/声望"""
        extras = tk.Frame(container, bg=C["bg"])
        extras.pack(fill="x", pady=2)

        if self.game.artifacts:
            tk.Label(extras, text="法宝: " + " ".join(self.game.artifacts),
                     font=self._sized_font(8), fg=C["gold"], bg=C["bg"]).pack(side="left", padx=5)
        if self.game.inventory:
            tk.Label(extras, text="丹药: " + " ".join(self.game.inventory),
                     font=self._sized_font(8), fg="#6b8e6b", bg=C["bg"]).pack(side="left", padx=5)
        if self.game.affinity:
            top_npc = sorted(self.game.affinity.items(), key=lambda x: x[1], reverse=True)[:3]
            npc_str = " ".join(f"{k}:{v}" for k, v in top_npc)
            tk.Label(extras, text="羁绊: " + npc_str,
                     font=self._sized_font(8), fg=C["text_dim"], bg=C["bg"]).pack(side="left", padx=5)
        rep = self.game.reputation
        if any(rep.values()):
            rp = f"正{rep['正道']} 魔{rep['魔道']} 散{rep['散修']}"
            tk.Label(extras, text="声望: " + rp,
                     font=self._sized_font(8), fg=C["accent"], bg=C["bg"]).pack(side="left", padx=5)

    # ============================================================
    # 成就检查
    # ============================================================
    def _check_achievements(self):
        new_achs = []
        total_attrs = sum(self.game.attrs.values())
        a = self.game.attrs

        checks = [
            ("初入仙途", lambda: len(self.game.path_history) >= 3),
            ("初露锋芒", lambda: len(self.game.path_history) >= 10),
            ("身经百战", lambda: len(self.game.path_history) >= 25),
            ("根骨过人", lambda: a.get("根骨", 0) >= 40),
            ("鸿运当头", lambda: a.get("幸运", 0) >= 40),
            ("魅力无双", lambda: a.get("魅力", 0) >= 40),
            ("意志如钢", lambda: a.get("精神", 0) >= 40),
            ("天资卓绝", lambda: a.get("悟性", 0) >= 40),
            ("全能修士", lambda: total_attrs >= 250),
            ("法宝收集者", lambda: len(self.game.artifacts) >= 3),
            ("炼丹大师", lambda: len(self.game.inventory) >= 5),
            ("人脉广阔", lambda: len(self.game.affinity) >= 3),
            ("正道之光", lambda: self.game.reputation.get("正道", 0) >= 10),
            ("散修传奇", lambda: self.game.reputation.get("散修", 0) >= 10),
            ("速通达人", lambda: self.timer_seconds > 0 and self.timer_seconds < 180),
            ("今日大吉", lambda: self.daily_fortune == "大吉"),
            ("不屈不挠", lambda: getattr(self, '_death_count', 0) >= 3),
            ("全结局达成", lambda: self.endings_count >= 46),
            ("十周目老玩家", lambda: self.endings_count >= 10),
            ("挑战者", lambda: self.game.challenge_mode),
        ]

        for name, condition in checks:
            if name not in self.achievements:
                try:
                    if condition():
                        self.achievements.add(name)
                        new_achs.append(name)
                except: pass

        if new_achs:
            self._save_persist()
            for ach in new_achs:
                self._toast(f"🏆 达成成就: {ach}")

        return new_achs

    # ============================================================
    # 章节背景
    # ============================================================
    def _draw_chapter_bg(self, chapter_num):
        bg_canvas = getattr(self, '_bg_canvas', None)
        if not bg_canvas:
            self._bg_canvas = tk.Canvas(self.content_canvas, highlightthickness=0, bg=C["panel"])
            self._bg_canvas.place(relwidth=1, relheight=1)
            bg_canvas = self._bg_canvas
        bg_canvas.delete("all")
        w, h = 800, 400
        colors = {"〇": ("#3a3020", "#2a2218"), "一": ("#3a3020", "#2a2218"),
                  "二": ("#4a4030", "#3a2a1a"), "三": ("#3a4a30", "#2a3a1a"),
                  "四": ("#4a3030", "#3a1a1a"), "五": ("#3a3040", "#2a1a3a"),
                  "六": ("#403a20", "#3a3010"), "七": ("#304030", "#1a301a"),
                  "八": ("#403030", "#301010"), "九": ("#303040", "#101030"),
                  "终": ("#303030", "#101010")}
        c1, c2 = colors.get(chapter_num[1] if len(chapter_num) > 1 else "一", colors["一"])
        # 简笔山峦
        for i in range(3):
            x0 = random.randint(50, 300) * (i + 1) * 0.5
            bg_canvas.create_arc(x0, h - 80 - i * 30, x0 + 300, h + 50, start=180, extent=180,
                                 fill=c2, outline="")
        # 月亮
        bg_canvas.create_oval(600, 50, 700, 150, fill="#c9a96e", outline="")

    # ============================================================
    # 设置面板
    # ============================================================
    def show_settings(self):
        self._clear_content()
        tk.Label(self.content_inner, text="设置", font=self._sized_font(16, "bold"),
                 fg=C["gold"], bg=C["panel"]).pack(pady=(30, 15))

        self._big_choice(self.content_inner, "T", f"切换主题 (当前: {'宣纸亮色' if self.theme == 'light' else '水墨暗色'})",
                        self._toggle_theme).pack(pady=3, fill="x", padx=30)
        sizes = {-1: "小", 0: "中", 1: "大"}
        self._big_choice(self.content_inner, "F", f"字号大小 (当前: {sizes[self.font_scale]})",
                        self._cycle_font_size).pack(pady=3, fill="x", padx=30)
        self._big_choice(self.content_inner, "B", f"背景音乐 ({'开' if self.bgm_on else '关'})",
                        self._toggle_bgm).pack(pady=3, fill="x", padx=30)
        self._big_choice(self.content_inner, "A", "成就列表", self.show_achievements).pack(pady=3, fill="x", padx=30)
        self._big_choice(self.content_inner, "N", "NPC 图鉴", self.show_npc_journal).pack(pady=3, fill="x", padx=30)
        self._big_choice(self.content_inner, "V", "结局树", self.show_ending_tree).pack(pady=3, fill="x", padx=30)
        self._big_choice(self.content_inner, "H", "今日运势", lambda: messagebox.showinfo(
            "今日运势", f"【{self.daily_fortune}】\n幸运值临时 {'+' if self.fortune_bonus >=0 else ''}{self.fortune_bonus}")).pack(pady=3, fill="x", padx=30)
        self._big_choice(self.content_inner, "C", "清空全部存档", self._clear_all_saves).pack(pady=3, fill="x", padx=30)

        self._big_choice(self.content_inner, "Esc", "返回主菜单", self.show_main_menu).pack(pady=15)
        self.root.bind("<Escape>", lambda e: self.show_main_menu())
        self._update_scroll()

    # ============================================================
    # 成就列表
    # ============================================================
    def show_achievements(self):
        all_achs = [
            "初入仙途", "初露锋芒", "身经百战", "根骨过人", "鸿运当头",
            "魅力无双", "意志如钢", "天资卓绝", "全能修士", "法宝收集者",
            "炼丹大师", "人脉广阔", "正道之光", "散修传奇", "速通达人",
            "今日大吉", "不屈不挠", "全结局达成", "十周目老玩家", "挑战者",
        ]
        self._clear_content()
        tk.Label(self.content_inner, text="成就列表", font=self._sized_font(16, "bold"),
                 fg=C["gold"], bg=C["panel"]).pack(pady=(30, 5))
        tk.Label(self.content_inner, text=f"已解锁: {len(self.achievements)} / {len(all_achs)}",
                 font=self._sized_font(10), fg=C["text_dim"], bg=C["panel"]).pack()

        for ach in all_achs:
            unlocked = ach in self.achievements
            icon = "★" if unlocked else "☆"
            color = C["gold"] if unlocked else C["text_dim"]
            tk.Label(self.content_inner, text=f"  {icon}  {ach}",
                     font=self._sized_font(11), fg=color, bg=C["panel"],
                     anchor="w").pack(fill="x", padx=40, pady=2)

        self._big_choice(self.content_inner, "Esc", "返回", self.show_settings).pack(pady=15)
        self.root.bind("<Escape>", lambda e: self.show_settings())
        self._update_scroll()

    # ============================================================
    # NPC 图鉴
    # ============================================================
    def show_npc_journal(self):
        npcs = {
            "青云真人": "隐世剑仙，你的第一位师父。遭仇家暗算落难时被你救起，授你《青云诀》。",
            "白眉道人": "玄天宗长老，慧眼识珠。在你击退山贼后邀你入门，后赠《玄天心经》。",
            "天魔老祖": "千年前被封印于古玉中的魔道巨擘，狡猾危险，试图夺舍你的肉身。",
            "太虚真君": "万年前的上古大能，留有洞府传承。但所谓'传承'可能是一个夺舍陷阱。",
            "药王谷主": "天下第一丹宗之主，赏识你的丹道天赋，邀你加入药王谷。",
        }
        self._clear_content()
        tk.Label(self.content_inner, text="NPC 图鉴", font=self._sized_font(16, "bold"),
                 fg=C["gold"], bg=C["panel"]).pack(pady=(30, 15))

        for name, bio in npcs.items():
            card = tk.Frame(self.content_inner, bg=C["btn_bg"], highlightbackground=C["border"],
                           highlightthickness=1)
            card.pack(fill="x", padx=20, pady=3)
            tk.Label(card, text=name, font=self._sized_font(11, "bold"), fg=C["gold"],
                     bg=C["btn_bg"], anchor="w").pack(padx=10, pady=(5, 0), fill="x")
            tk.Label(card, text=bio, font=self._sized_font(9), fg=C["text_dim"],
                     bg=C["btn_bg"], anchor="w", wraplength=650, justify="left").pack(padx=10, pady=(0, 8), fill="x")

        self._big_choice(self.content_inner, "Esc", "返回", self.show_settings).pack(pady=15)
        self.root.bind("<Escape>", lambda e: self.show_settings())
        self._update_scroll()

    # ============================================================
    # 结局树可视化
    # ============================================================
    def show_ending_tree(self):
        self._clear_content()
        tk.Label(self.content_inner, text="结局树", font=self._sized_font(16, "bold"),
                 fg=C["gold"], bg=C["panel"]).pack(pady=(30, 5))

        canvas = tk.Canvas(self.content_inner, width=700, height=300, bg=C["panel"], highlightthickness=0)
        canvas.pack(pady=10)

        gallery_file = os.path.join(SAVE_DIR, "_gallery.json")
        unlocked = set()
        if os.path.exists(gallery_file):
            with open(gallery_file, "r", encoding="utf-8") as f:
                unlocked = {e.get("title", "") for e in json.load(f)}

        # 简化的树状图：主分支 + 叶节点
        branches = {
            "剑修": ("剑神降世", "堕入魔道", "正道砥柱", "逍遥剑仙", "妖仙至尊", "青霜剑侠"),
            "丹修": ("丹剑宗师", "走火入魔", "丹圣临世", "仁心圣手", "丹武双绝", "疯丹仙"),
            "宗门": ("一代掌门", "宗门英烈", "散修传奇", "王者归来"),
            "散修": ("太虚传人", "凡人善终", "大器晚成", "一方守护", "博古通今"),
            "古玉": ("神魂俱灭", "自强不息", "一体两面", "心魔之主"),
            "商道": ("财可通神", "凡尘圆满", "富甲三界", "功德成仙"),
        }

        y = 40
        for branch, endings in branches.items():
            x = 60
            canvas.create_text(x, y, text=branch, font=self._sized_font(10, "bold"),
                              fill=C["gold"], anchor="w")
            canvas.create_line(x + 50, y, x + 80, y, fill=C["border"])
            x += 85
            for end in endings:
                is_unlocked = any(end in u for u in unlocked)
                color = C["gold"] if is_unlocked else C["text_dim"]
                icon = "●" if is_unlocked else "○"
                canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill=color, outline="")
                canvas.create_text(x + 15, y, text=f"{icon}{end}", font=self._sized_font(8),
                                  fill=color, anchor="w")
                x += max(90, len(end) * 9 + 20)
            y += 42

        canvas.configure(scrollregion=canvas.bbox("all"))
        self._big_choice(self.content_inner, "Esc", "返回", self.show_settings).pack(pady=10)
        self.root.bind("<Escape>", lambda e: self.show_settings())
        self._update_scroll()

    # ============================================================
    # 导出 / 截图 / TTS
    # ============================================================
    def _export_ending_text(self):
        text = f"【仙途 · 文字修仙 — 通关记录】\n\n"
        text += f"角色: {self.game.player_name}  词条: {self.game.trait}\n"
        text += f"最终属性: {self.game.attrs}\n"
        text += f"法宝: {self.game.artifacts or '无'}\n"
        text += f"决策轮数: {len(self.game.path_history)}\n\n"
        text += "——— 剧情路径 ———\n\n"
        for i, nid in enumerate(self.game.path_history):
            node = NODES.get(nid, {})
            text += f"{i+1}. {node.get('title', nid)}\n"
        end_node = NODES.get(self.game.current_node, {})
        text += f"\n★ {end_node.get('title', '结局')}\n"

        filename = f"通关记录_{self.game.player_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(text)
        self._toast(f"已导出: {filename}")

    def _take_screenshot(self):
        try:
            x = self.root.winfo_rootx()
            y = self.root.winfo_rooty()
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            import io
            from PIL import ImageGrab
            img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
            filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            img.save(filename)
            self._toast(f"截图已保存: {filename}")
        except:
            self._toast("截图失败，需要安装 Pillow: pip install pillow")

    def _tts_speak(self, text):
        try:
            import win32com.client
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            speaker.Speak(text)
        except:
            pass  # 静默失败，不影响游戏

    # ============================================================
    # 速通计时
    # ============================================================
    def _start_timer(self):
        if not self.timer_running:
            self.timer_running = True
            self.timer_seconds = 0
            self.game.start_time = time.time()
            self._tick_timer()

    def _tick_timer(self):
        if self.timer_running and self.game.start_time:
            self.timer_seconds = int(time.time() - self.game.start_time)
            self.root.after(1000, self._tick_timer)

    def _stop_timer(self):
        self.timer_running = False

    # ============================================================
    # 启动时注入运势和计时
    # ============================================================
    def _start_game_with_extras(self):
        """覆盖 _start_game，注入运势加成和计时"""
        g = self.game
        trait_key = self.selected_trait
        if trait_key in TRAITS:
            g.trait = TRAITS[trait_key]["name"]
            for name, bonus in TRAITS[trait_key]["bonus"].items():
                self.attrs[name] = self.attrs.get(name, 0) + bonus
        g.attrs = self.attrs
        g.attrs["幸运"] = g.attrs.get("幸运", 0) + self.fortune_bonus
        g.current_node = "start"
        g.path_history = []
        g.artifacts = []
        g.inventory = []
        g.affinity = {}
        g.reputation = {"正道": 0, "魔道": 0, "散修": 0}
        self.last_chapter = ""
        self.auto_save_file = ""
        self._start_timer()
        self.render_current_node()

    # ============================================================
    # 在 _make_choice 后注入法宝/声望等
    # ============================================================
    def _inject_gameplay_rewards(self):
        """每次选择后检查是否触发奖励"""
        nid = self.game.current_node
        # 法宝奖励 — 特定节点
        artifact_nodes = {
            "sword_tactic": "妖丹",
            "give_core": "青霜剑",
            "end_breakthrough": "妖灵珠",
            "end_inheritance": "太虚令",
            "end_saint": "药王鼎",
            "end_hero": "侠义勋章",
        }
        if nid in artifact_nodes and artifact_nodes[nid] not in self.game.artifacts:
            self.game.artifacts.append(artifact_nodes[nid])
            self._toast(f"获得法宝: {artifact_nodes[nid]}")

        # 声望
        rep_map = {
            "end_alliance": ("正道", 5), "end_leader": ("正道", 4), "end_hero": ("正道", 3),
            "end_fallen": ("魔道", 5), "end_possessed": ("魔道", 4),
            "end_isolate": ("散修", 4), "end_wander": ("散修", 3),
        }
        if nid in rep_map:
            faction, val = rep_map[nid]
            self.game.reputation[faction] += val

        # 好感度
        if "师父" in str(NODES.get(nid, {}).get("text", ""))[:50]:
            self.game.affinity["师父"] = self.game.affinity.get("师父", 30) + 2
        if "白眉" in str(NODES.get(nid, {}).get("text", ""))[:50]:
            self.game.affinity["白眉道人"] = self.game.affinity.get("白眉道人", 20) + 2

    # ============================================================
    # 快捷键绑定（F12截图, Ctrl+E导出, Ctrl+T TTS）
    # ============================================================
    def _bind_global_keys(self):
        self.root.bind("<F12>", lambda e: self._take_screenshot())
        self.root.bind("<Control-e>", lambda e: self._export_ending_text())
        self.root.bind("<Control-t>", lambda e: self._tts_speak(
            NODES.get(self.game.current_node, {}).get("text", "")))
        self.root.bind("<Control-z>", lambda e: self._undo_choice())
        self.root.bind("<question>", lambda e: self._show_shortcuts())

    # ============================================================
    # 撤销 / 快捷键帮助 / 清空存档 / 跳过已读
    # ============================================================
    def _undo_choice(self):
        if not self.undo_stack:
            self._toast("无法撤销")
            return
        prev_node, prev_history = self.undo_stack.pop()
        self.game.current_node = prev_node
        self.game.path_history = prev_history
        self.render_current_node()
        self._toast("已撤销")

    def _show_shortcuts(self):
        text = (
            "【快捷键速查】\n\n"
            "  1-9      选择对应选项\n"
            "  S        保存进度\n"
            "  Esc      返回主菜单\n"
            "  ↑↓←→    属性分配界面导航\n"
            "  Enter    确认\n"
            "  Ctrl+Z   撤销上一步\n"
            "  Ctrl+E   导出通关文本\n"
            "  Ctrl+T   TTS 朗读\n"
            "  F12      截图\n"
            "  ?        显示此帮助\n"
        )
        messagebox.showinfo("快捷键", text)

    def _clear_all_saves(self):
        if not messagebox.askyesno("确认", "确定要删除所有存档吗？\n此操作不可恢复！"):
            return
        import glob
        for f in glob.glob(os.path.join(SAVE_DIR, "*.json")):
            os.remove(f)
        self.cleared_chapters.clear()
        self.achievements.clear()
        self.endings_count = 0
        self._save_persist()
        self._toast("所有存档已清除")

    # ============================================================
    # 战斗 HP 可视化
    # ============================================================
    def _draw_hp_bar(self, canvas, x, y, w, h, current, max_val, label=""):
        canvas.create_text(x, y - 8, text=label, font=(*FONT, 10), fill=C["text"], anchor="w")
        canvas.create_rectangle(x, y, x + w, y + h, outline=C["border"], fill=C["border"])
        pct = max(0, current / max(max_val, 1))
        color = "#6b8e6b" if pct > 0.5 else "#c9a96e" if pct > 0.2 else C["danger"]
        canvas.create_rectangle(x, y, x + w * pct, y + h, fill=color, outline="")
        canvas.create_text(x + w / 2, y + h / 2, text=f"{current}/{max_val}",
                          font=(*FONT, 8, "bold"), fill=C["white"])

    # ============================================================
    # 加载画面
    # ============================================================
    def _show_splash(self):
        splash = tk.Toplevel(self.root)
        splash.overrideredirect(True)
        splash.configure(bg=C["bg"])
        splash.geometry("400x250")
        # 居中
        splash.update_idletasks()
        sw, sh = splash.winfo_width(), splash.winfo_height()
        rw = self.root.winfo_screenwidth()
        rh = self.root.winfo_screenheight()
        splash.geometry(f"+{(rw - 400) // 2}+{(rh - 250) // 2}")

        tk.Label(splash, text="仙 途", font=(*FONT, 28, "bold"),
                 fg=C["gold"], bg=C["bg"]).pack(pady=(60, 5))
        tk.Label(splash, text="文 字 修 仙", font=(*FONT, 12),
                 fg=C["text_dim"], bg=C["bg"]).pack()
        tk.Label(splash, text="墨染江湖 · 一字一世界", font=(*FONT, 9),
                 fg=C["text_dim"], bg=C["bg"]).pack(pady=(15, 0))

        # 1.5秒后关闭
        splash.after(1500, splash.destroy)

    def run(self):
        self._bind_global_keys()
        self.root.mainloop()


if __name__ == "__main__":
    app = XianTuApp()
    app.run()
