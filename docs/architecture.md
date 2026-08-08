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
`achievement_system.py` 读取 `data/achievements.json`，Web 端在结局记录后统一更新解锁状态；`theme_tokens.py` 只属于桌面端展示层。

## Data boundaries

- `data/`：可提交的设计数据。
- `static/`：可提交的 Web 资源。
- `saves/`：运行时用户数据，禁止提交。
- `dist/`、`build/`、`exports/`、`__pycache__/`：生成物，禁止提交。

运行时目录可以通过 `XIANTU_SAVE_DIR` 外置，剧情可以通过 `XIANTU_STORY_FILE` 指定测试数据。

## Adding a branch

1. 在 `data/story_nodes.json` 添加节点和 `next`/`fail` 目标。
2. 用 `story_editor.py validate` 检查格式。
3. 用 `story_tools.py quality` 检查可达性与结局数量。
4. 若新增资源或收集品，在 `playability.py` 添加规则并补测试。
5. 同时运行编译、单元测试和一次 Web API 烟测。

不要在 `server.py` 或 `app.py` 中重新实现剧情判定；如果规则需要变化，优先修改核心引擎或玩法模块。
