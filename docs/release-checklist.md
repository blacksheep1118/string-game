# GitHub release checklist

- [ ] `git status --short --ignored` 中没有应上传的存档、缓存或导出物。
- [ ] `python3 story_tools.py validate` 通过。
- [ ] `python3 story_tools.py quality` 显示所有节点可达。
- [ ] `PYTHONPYCACHEPREFIX=/tmp/xiantu-pycache python3 -m compileall -q .` 通过。
- [ ] `python3 -m unittest discover -s tests -v` 通过。
- [ ] Web 版可创建角色、做出选择、保存、读取并记录结局。
- [ ] `README.md` 的玩法与规模以当前 `data/` 统计为准。
- [ ] 只提交源代码、剧情/成就数据、静态资源、测试和文档。
