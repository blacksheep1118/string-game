# -*- coding: utf-8 -*-
"""仙途 · 文字修仙 — 原生桌面版（tkinter，零额外依赖）"""
import json
import os
import sys
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
        self.root.geometry("880x680")
        self.root.minsize(600, 480)
        self.root.configure(bg=C["bg"])

        self.game = Game()
        self.last_chapter = ""
        self.auto_save_file = ""

        # 关闭窗口确认
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._setup_styles()
        self._build_ui()
        self.show_main_menu()

    def _on_close(self):
        if messagebox.askyesno("退出游戏", "确定要退出吗？\n未保存的进度将丢失。"):
            self.root.destroy()

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

        # 属性面板
        self.attrs_frame = tk.Frame(self.root, bg=C["bg"], height=35)
        self.attrs_frame.pack(fill="x", padx=30, pady=(3, 0))

        # 底部按钮
        bottom = tk.Frame(self.root, bg=C["bg"])
        bottom.pack(fill="x", padx=30, pady=(0, 15))

        self._btn(bottom, "保存进度", self.save_game, C["text_dim"]).pack(side="left", padx=4)
        self._btn(bottom, "读取存档", self.show_load_dialog, C["text_dim"]).pack(side="left", padx=4)
        self._btn(bottom, "重新开始", self.restart_game, C["text_dim"]).pack(side="left", padx=4)
        self._btn(bottom, "结局画廊", self.show_gallery, C["text_dim"]).pack(side="left", padx=4)
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
        max_val = 60
        for name in ATTR_NAMES:
            v = self.game.attrs.get(name, 0)
            pct = min(100, int(v / max_val * 100))
            f = tk.Frame(self.attrs_frame, bg=C["bg"])
            f.pack(side="left", padx=6)
            tk.Label(f, text=f"{name} {v}", font=(*FONT, 9, "bold"),
                     fg=C["gold"], bg=C["bg"]).pack(side="left", padx=(0, 3))
            bar_canvas = tk.Canvas(f, width=50, height=5, bg=C["border"], highlightthickness=0)
            bar_canvas.pack(side="left")
            bar_canvas.create_rectangle(0, 0, pct / 100 * 50, 5, fill=C["gold"], outline="")

    def _auto_save(self, chapter):
        if chapter and chapter != self.last_chapter and self.last_chapter:
            self._do_save(overwrite=self.auto_save_file)
            if not self.auto_save_file:
                # first save — find the file we just created
                saves_dir = SAVE_DIR
                if os.path.exists(saves_dir):
                    files = sorted([f for f in os.listdir(saves_dir) if f.startswith("save_")], reverse=True)
                    if files:
                        self.auto_save_file = files[0]
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

        self._big_choice(self.content_inner, "1", "开始新游戏", self.show_new_game_name).pack(pady=4)
        self._big_choice(self.content_inner, "2", "读取存档", self.show_load_dialog).pack(pady=4)
        self._big_choice(self.content_inner, "3", "结局画廊", self.show_gallery).pack(pady=4)

        self.root.bind("1", lambda e: self.show_new_game_name())
        self.root.bind("2", lambda e: self.show_load_dialog())
        self.root.bind("3", lambda e: self.show_gallery())

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
        self._big_choice(self.content_inner, "Enter", "开始游戏", self._start_game).pack(pady=20)

        # 键盘：1-6 选词条，Enter 确认
        for k in sorted(TRAITS.keys(), key=int):
            self.root.bind(k, lambda e, key=k: self._select_trait(key))
        self.root.bind("<Return>", lambda e: self._start_game())
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
            self._choice_callbacks = {}
            for i, c in enumerate(choices):
                idx = i
                cb = lambda n=idx: self._make_choice(n)
                self._choice_callbacks[i] = cb
                self._big_choice(self.content_inner, str(i + 1), c["text"], cb
                                ).pack(pady=3, fill="x", padx=30)
            for i in range(len(choices)):
                key = str(i + 1)
                self.root.bind(key, lambda e, n=i: self._make_choice(n))
            # S 键存档
            self.root.bind("s", lambda e: self.save_game())
            self.root.bind("S", lambda e: self.save_game())
            # Esc 回主菜单
            self.root.bind("<Escape>", lambda e: self.show_main_menu())

        self._render_attrs()
        self._update_scroll()

    def _show_ending_summary(self, node):
        tk.Frame(self.content_inner, bg=C["panel"], height=15).pack()

        # 记录结局
        self._record_ending()

        # 属性总结
        summary = tk.Frame(self.content_inner, bg=C["btn_bg"], highlightbackground=C["border"], highlightthickness=1)
        summary.pack(fill="x", padx=30, pady=10)

        tk.Label(summary, text="通关总结", font=(*FONT, 12, "bold"),
                 fg=C["gold"], bg=C["btn_bg"]).pack(pady=(10, 5))
        tk.Label(summary, text=f"词条: {self.game.trait}",
                 font=(*FONT, 10), fg=C["text_dim"], bg=C["btn_bg"]).pack()

        for k in ATTR_NAMES:
            v = self.game.attrs.get(k, 0)
            bar = "█" * min(20, v // 3) + "░" * max(0, 20 - v // 3)
            tk.Label(summary, text=f"  {k}: {v:>3}  {bar}",
                     font=(*FONT, 9), fg=C["text"], bg=C["btn_bg"]).pack(anchor="w", padx=40)

        tk.Frame(self.content_inner, bg=C["panel"], height=10).pack()

        self._big_choice(self.content_inner, "1", "重新开始", self.show_new_game_name).pack(pady=3, fill="x", padx=30)
        self._big_choice(self.content_inner, "2", "返回主菜单", self.show_main_menu).pack(pady=3, fill="x", padx=30)

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

    def _make_choice(self, idx):
        node = NODES.get(self.game.current_node)
        if not node:
            return
        choices = node.get("choices", [])
        if idx >= len(choices):
            return

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
    def _big_choice(self, parent, idx_str, text, cmd):
        btn = tk.Button(parent, text=f"  [{idx_str}]  {text}",
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

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = XianTuApp()
    app.run()
