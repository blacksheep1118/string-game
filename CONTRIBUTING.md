# Contributing

请把剧情改动放在 `data/story_nodes.json`，把规则改动放在 `xiantu/` 或 `playability.py`，不要在不同前端复制一套结算逻辑。

提交前运行：

```bash
python3 story_tools.py validate
python3 story_tools.py quality
PYTHONPYCACHEPREFIX=/tmp/xiantu-pycache python3 -m compileall -q .
python3 -m unittest discover -s tests -v
```

运行生成的存档和缓存应保持在本地，不要加入提交。
