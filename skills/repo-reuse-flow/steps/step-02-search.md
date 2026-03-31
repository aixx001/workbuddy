# Step 2: 仓库搜索 (search)

**触发条件**: `outputs/02_candidates/candidates.json` 不存在

**可跳过**: 如果 `state.target_repos` 已预设目标仓库

## 执行步骤

1. 读取 `outputs/01_demand/demand.json` 中的关键词
2. 运行搜索脚本：
   ```bash
   .venv\Scripts\python.exe scripts/02_repo_search.py
   ```
3. 按评分排序，取 Top 5-10
4. 生成 `outputs/02_candidates/candidates.json`

## 搜索策略

- GitHub Search API + 关键词组合
- 按 stars、recent commits、license 筛选
- 参考 `references/github_search_guide.md` 和 `references/scoring_template.md`

## 完成检查

- [ ] `outputs/02_candidates/candidates.json` 存在
- [ ] 至少 3 个候选仓库
