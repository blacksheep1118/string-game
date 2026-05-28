# 仙途 · 文字修仙

水墨画风修仙文字游戏。256 个剧情节点，30 轮决策深度，6 条主线，46 种结局。

---

## 快速开始

### 桌面版（推荐）

Windows：双击 **`run_gui.bat`** 或 **`run_gui.pyw`**（无控制台窗口）。

macOS：双击 **`run_gui.command`**，或在终端运行：

```bash
python3 run_gui.pyw
```

纯 Python tkinter 实现，零额外依赖。窗口动画、水墨主题、键盘/鼠标双操作。

### 终端版

```bash
python game.py
```

也可以使用统一启动器：

```bash
python launcher.py desktop
python launcher.py web --lan
python launcher.py terminal
```

### 浏览器版

```bash
pip install flask
python server.py
# 浏览器访问 http://127.0.0.1:5000
```

Windows 可双击 **`run_web.bat`**，macOS 可双击 **`run_web.command`**。这两个脚本会监听局域网地址，方便手机访问。

手机访问方式：

1. 让电脑和手机连接同一个 Wi-Fi。
2. 启动 `run_web.bat` 或 `run_web.command`。
3. 在手机浏览器打开终端里显示的 `http://电脑局域网IP:5000` 地址。

如需手动指定：

```bash
python server.py --host 0.0.0.0 --port 5000
python server.py --host 127.0.0.1 --port 5000 --no-browser
```

### 打包 EXE

双击 **`build_exe.bat`**，生成 `dist/XianTu.exe` 单文件独立运行。

macOS 可运行：

```bash
./build_macos.command
```

---

## 功能一览

### 核心系统

| 功能 | 说明 |
|------|------|
| 角色创建 | 100 点自由分配 5 项属性 + 6 选 1 词条 |
| 属性判定 | 隐藏需求，不足时走艰难路线 |
| 隐藏加成 | 54 个选项会悄悄增减属性，行末 `《+2根骨》` 预览 |
| 章节自动存档 | 章间覆盖式保存，一局只留一个文件 |
| 手动存档 | 随时保存留关键节点，弹窗支持删除 |
| 存档导入导出 | 浏览器版支持 JSON 存档导入、导出和跨设备迁移 |
| 存档版本迁移 | 存档带 `schema_version`，旧存档会自动补齐字段 |
| 键盘全操作 | 所有界面均可键盘完成，`?` 查看快捷键 |

### 重玩与收集

| 功能 | 说明 |
|------|------|
| 结局画廊 | 46 个结局卡片，各自独有图标和评价标签 |
| 全结局彩蛋 | 集齐 46 个解锁 SS+ 隐藏结局 |
| 结局树 | Canvas 树状分支图，已解锁 ● 未解锁 ○ |
| 成就系统 | 20 个自动检测成就，弹窗提示 |
| 排行榜 | 按评分排序，记录玩家/结局/用时/决策数 |
| 章节选择 | 通关后可跳转任意已解锁章节 |
| 剧情回放 | 结局后逐页回顾完整决策路径 |
| 速通计时 | 自动计时，结局显示通关用时 |

### 沉浸体验

| 功能 | 说明 |
|------|------|
| 暗雷事件 | 5% 概率触发，幸运越高事件越好 |
| 回合制战斗 | 弹窗攻击/防御，根骨+伤害 精神+格挡 |
| 炼丹小游戏 | 丹修节点控火选择，完美控火 +3 悟性 |
| 法宝收集 | 青霜剑/妖灵珠/太虚令等自动获得 |
| 阵营声望 | 正道/魔道/散修三维声望 |
| 好感度 | NPC 羁绊值追踪 |
| NPC 图鉴 | 5 位核心角色小传 |
| ASCII 立绘 | 属性栏右侧随修为变化 |

### 界面增强

| 功能 | 说明 |
|------|------|
| 水墨/宣纸双主题 | 设置页一键切换 |
| 字号三档可调 | 小/中/大 |
| PWA 支持 | 浏览器版可添加到手机主屏幕，核心静态资源可离线缓存 |
| 响应式适配 | 支持桌面、小窗口、平板和手机竖屏布局 |
| BGM 古风循环 | 右下角 🔊/🔇 切换 |
| 窗口记忆 | 关闭时自动保存位置/大小 |
| 加载画面 | 启动水墨过渡 1.5 秒 |
| F12 截图 | PNG 格式保存 |
| Ctrl+E 导出 | 通关文本导出 .txt |
| Ctrl+T 朗读 | Windows TTS 语音播报 |
| Ctrl+Z 撤销 | 回退上一个选择 |
| 今日运势 | 大吉~末吉，影响开局幸运 |

---

## 角色属性

| 属性 | 影响 |
|------|------|
| 根骨 | 战斗、肉身 |
| 幸运 | 机缘、寻宝 |
| 魅力 | 社交、交易 |
| 精神 | 意志、心魔 |
| 悟性 | 学习、功法 |

## 初始词条

天生剑骨（根骨+10） · 天命所归（幸运+15） · 龙凤之姿（魅力+15）
心如磐石（精神+15） · 七窍玲珑（悟性+15） · 天道酬勤（各项+4）

---

## 六条主线 · 结局评价 D ~ SS

剑修 · 丹修 · 宗门 · 散修 · 古玉 · 商道

---

## 快捷键速查

| 按键 | 功能 |
|------|------|
| `1`-`9` | 选择选项 |
| `S` | 保存 |
| `Esc` | 返回主菜单 |
| `↑↓←→` | 属性分配导航 |
| `Enter` | 确认 |
| `Ctrl+Z` | 撤销 |
| `Ctrl+E` | 导出文本 |
| `Ctrl+T` | TTS 朗读 |
| `F12` | 截图 |
| `?` | 速查帮助 |

---

## 开发工具

### 校验剧情节点

```bash
python story_tools.py validate
```

### 导出剧情数据

```bash
python story_tools.py export --output data/story_nodes.json
```

游戏会优先读取 `data/story_nodes.json`，也可以通过环境变量指定：

```bash
XIANTU_STORY_FILE=/path/to/story_nodes.json python server.py
```

### 编辑剧情 JSON

```bash
python story_editor.py list
python story_editor.py show start
python story_editor.py set-title start "序章 · 新标题"
python story_editor.py validate
```

### 本地检查

```bash
python -m compileall -q .
python -m unittest discover -s tests
```

GitHub Actions 会自动运行语法检查、剧情校验和单元测试。

---

## 项目结构

```
文字游戏/
├── app.py             # 桌面版主程序（tkinter）
├── game.py            # 游戏引擎
├── save_manager.py    # 三端共用存档管理
├── theme_tokens.py    # 桌面/Web 共用颜色令牌
├── story_tools.py     # 剧情校验/导出工具
├── story_editor.py    # 剧情 JSON 命令行编辑器
├── launcher.py        # 跨平台统一启动器
├── server.py          # 浏览器版后端（Flask）
├── data/story_nodes.json # 外置剧情数据
├── static/index.html  # 浏览器版 HTML
├── static/style.css   # 浏览器版样式
├── static/app.js      # 浏览器版逻辑
├── static/manifest.json
├── static/service-worker.js
├── run_gui.bat/pyw    # 桌面版启动器
├── run_gui.command    # macOS 桌面版启动器
├── run.bat            # 终端版启动器
├── run_web.bat        # Windows 浏览器版/手机访问启动器
├── run_web.command    # macOS 浏览器版/手机访问启动器
├── build_exe.bat      # 打包脚本
├── build_macos.command
├── XianTu.spec        # PyInstaller 打包配置
├── tests/             # 自动化检查
├── requirements.txt   # 依赖
├── saves/             # 存档/画廊/成就/排行榜
└── README.md
```

---

## 常见问题

**Q: 桌面版启动报错？**

A: 确保 Python 3.7+ 已安装，tkinter 为 Python 自带无需额外安装。

**Q: 截图功能报错？**

A: 需要 `pip install pillow` 安装 Pillow 库。

**Q: TTS 不工作？**

A: 需要 `pip install pywin32`，且系统已安装中文语音包。

**Q: 打包 EXE 失败？**

A: `pip install pyinstaller` 后运行 `build_exe.bat`。
