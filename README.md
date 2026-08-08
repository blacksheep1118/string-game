# 仙途 · 文字修仙

一款以选择为核心的中文文字修仙游戏。当前剧情数据包含 **330 个节点、79 个剧情结局**，收集全部剧情结局后还可解锁 1 个隐藏结算：每次选择会改变属性、资源、声望、羁绊和收集品，低属性判定还会把你带入另一条命运分支。

需要 Python **3.10+**。Flask 只用于 Web 入口，桌面和终端入口使用 Python 标准库。

游戏提供 Web、桌面和终端三种入口。剧情只有一份规范来源，三种入口共享同一套状态与选择结算。

## 快速开始

### Web 版

```bash
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python server.py --no-browser
```

打开 <http://127.0.0.1:5000>。需要手机访问时运行 `python server.py --host 0.0.0.0`，并使用电脑局域网地址。

### 终端版

终端版只依赖 Python 标准库：

```bash
python3 game.py
```

### 桌面版

macOS 运行 `./run_gui.command`，Windows 双击 `run_gui.bat`。桌面版使用 tkinter，不需要 Flask。

## 玩法

- 100 点自由分配五项属性，再选择一个初始词条。
- 剑修、丹修、宗门、散修、古玉、商道六个主路线，另有魔道、御兽、炼器、阵法、时间和双修等支线流派。
- 选择会触发属性判定、失败分支、路线奖励、随机奇遇、法宝/丹药收集和声望变化。
- 结局画廊、排行榜、成就、命运图谱、快速轮回和跨设备 JSON 存档支持重复探索。
- Web、终端和桌面端共享路线试炼状态；Web 端支持响应式布局、键盘操作、PWA、主题/字号/音效设置，桌面端额外提供炼丹控火与剑修实战试炼。

## 仓库结构

```text
.
├── data/                    # 可编辑的剧情与成就 JSON
├── xiantu/                  # 平台无关核心：路径、剧情加载、状态、结算、终端 UI
│   ├── config.py
│   ├── engine.py
│   ├── story.py
│   └── terminal.py
├── server.py                # Flask Web API 与静态资源服务
├── app.py                   # tkinter 桌面端
├── game.py                  # 终端兼容入口与旧脚本导出
├── playability.py           # 奖励、奇遇、路线、评分、持久化结算和成就上下文
├── save_manager.py          # 存档迁移、校验、导入导出
├── achievement_system.py    # 数据驱动成就定义与解锁状态
├── theme_tokens.py          # 桌面端主题令牌
├── static/                  # Web 前端、PWA 与动画
├── tests/                   # API、静态资源、存档和剧情图测试
└── story_tools.py           # 剧情校验、质量报告和导出工具
```

`data/story_nodes.json` 是唯一剧情数据源；不要再把节点复制回 Python 文件。新增节点后运行校验即可确认引用和可达性。

## 玩家数据与 Git

存档、画廊、成就、排行榜、进度和桌面设置都属于本地运行数据，仓库不会上传它们。`.gitignore` 会忽略 `saves/*.json`、Python 缓存、打包目录和临时导出物。

也可以把玩家数据放到仓库外：

```bash
XIANTU_SAVE_DIR=/path/to/xiantu-data python server.py --no-browser
```

如果某个旧版本曾经把存档或 `__pycache__` 提交过，需要执行一次：

```bash
git rm --cached -r __pycache__ saves
```

该命令只从 Git 索引移除，保留本地文件。

## 开发检查

```bash
python3 story_tools.py validate
python3 story_tools.py quality
PYTHONPYCACHEPREFIX=/tmp/xiantu-pycache python3 -m compileall -q .
python3 -m unittest discover -s tests -v
```

CI 会安装 `requirements.txt` 后执行同一组检查。Web API 测试需要 Flask；没有安装依赖时可先运行剧情、存档和静态资源测试。

## 剧情编辑

```bash
python3 story_editor.py list
python3 story_editor.py show start
python3 story_editor.py set-title start "序章 · 新标题"
python3 story_editor.py validate
```

编辑完成后至少检查：目标节点存在、所有节点从 `start` 可达、终端节点有 `choices: []`，以及每个选择有 `next` 或 `fail`。
