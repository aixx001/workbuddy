# Step 4: 依赖图 (depgraph)

**触发条件**: `outputs/04_depgraph/` 下无 JSON 文件

**加载 Skill**: `skills/dep-graph`

## 执行步骤

1. **对每个 structure.json 构建依赖图**
   ```bash
   .venv\Scripts\python.exe scripts/build_dep_graph.py \
     outputs/03_analysis/structures/<repo>_structure.json \
     -o outputs/04_depgraph/<repo>_depgraph.json
   ```

2. **分析结果**，重点关注：
   - `communities` — 自动检测到的模块簇
   - `leaf_nodes` — 零依赖，最容易提取
   - `hub_nodes` — 核心枢纽，不建议单独提取

3. **确定提取候选**
   - 参考 Skill 中的决策指南（reuse_score 阈值）

## 完成检查

- [ ] `outputs/04_depgraph/*.json` 至少有一个文件
- [ ] JSON 包含 `nodes` 和 `communities` 字段
