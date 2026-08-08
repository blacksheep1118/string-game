# Architecture

## Runtime flow

```text
data/story_nodes.json
        │
        ▼
xiantu.story ──► xiantu.engine ──► playability / save_manager
        │                 │
        ├──────────────► server.py ──► static/
        ├──────────────► app.py
        └──────────────► xiantu.terminal ──► game.py
```

`xiantu.engine.resolve_choice()` 是所有前端的选择结算入口。它负责应用选项效果、检查属性需求、选择成功/失败目标、发放节点奖励、触发奇遇并生成反馈；前端只负责展示。
`playability.py` 负责跨入口共享的资源、路线、评分、画廊/排行榜/轮回进度和成就上下文；`achievement_system.py` 读取 `data/achievements.json`，Web、桌面和终端都通过共享层写入同一份 `_achievements.json`。`theme_tokens.py` 只属于桌面端展示层。
路线试炼、全结局后的隐藏结算也由 `playability.py` 统一落盘，Web、终端和桌面端使用相同的 `minigames` 状态标记，避免跨入口重复刷奖励。
每个 `Game` 持有独立随机数发生器，随机状态进入撤销快照和 JSON 存档，保证继续游戏与撤销重放可复现。路线优先读取节点的显式 `route` 字段，其次使用稳定的节点 ID 映射，剧情文本只作为兼容旧数据的兜底。

## Data boundaries

- `data/`：可提交的设计数据。
- `static/`：可提交的 Web 资源。
- `saves/`：运行时用户数据，禁止提交。
- `dist/`、`build/`、`exports/`、`__pycache__/`：生成物，禁止提交。
- `_gallery.json`、`_leaderboard.json`、`_achievements.json`、`_progression.json` 和 `_persist.json`：玩家运行数据，禁止提交。

运行时目录可以通过 `XIANTU_SAVE_DIR` 外置，剧情可以通过 `XIANTU_STORY_FILE` 指定测试数据。

## Adding a branch

1. 在 `data/story_nodes.json` 添加节点和 `next`/`fail` 目标。
2. 用 `story_editor.py validate` 检查格式。
3. 用 `story_tools.py quality` 检查可达性与结局数量。
4. 若新增资源、收集品或小游戏，在 `playability.py` 添加规则并补测试；不要只在某个界面写一套结算。
5. 同时运行编译、单元测试和一次 Web API 烟测。

不要在 `server.py` 或 `app.py` 中重新实现剧情判定；如果规则需要变化，优先修改核心引擎或玩法模块。
