---
description: "repo-reuse-flow 完整工作流编排 — 状态机驱动的 6 阶段流程"
---

# Repo Reuse Flow — 工作流编排

一个命令，完成从需求分析到模块上架的完整复用流程。自动跳过已完成的阶段。

## 使用方法

```
/repo-reuse                    # 启动/继续完整流程
/repo-reuse reset              # 重置状态，从头开始
/repo-reuse status             # 查看当前进度
/repo-reuse skip               # 跳过当前阶段
/repo-reuse goto <phase>       # 跳转到指定阶段
```

## 工作流阶段

| 阶段 | 名称 | 产出物 | 检查点 |
|------|------|--------|--------|
| 1 | 需求收集 (demand) | `outputs/01_demand/demand.json` | ✓ JSON 存在且有 keywords |
| 2 | 仓库搜索 (search) | `outputs/02_candidates/candidates.json` | ✓ 至少 3 个候选 |
| 3 | 仓库分析 (analyze) | `outputs/03_analysis/structures/*.json` | ✓ AST 结构文件存在 |
| 4 | 依赖图 (depgraph) | `outputs/04_depgraph/*.json` | ✓ 有 nodes + communities |
| 5 | 模块提取 (extract) | `05_modules/` 或 `06_module_market/python/modules/` | ✓ 模块目录存在 |
| 6 | 模块上架 (market) | `workflows/verify_*.py` + `python/results/eval_*.json` + 前端 5 tab | ✓ 评估结论"可用" |

---

## 初始化

### 1. 加载状态

检查状态文件 `.reuse-state.yaml`（模板见 `state-template.yaml`）：

- 如果不存在 → 从模板创建，进入 Phase 1
- 如果存在 → 读取 `current_phase`，从该阶段继续

### 2. 跳过逻辑

对于每个阶段：
1. 状态文件中标记为 `completed`？→ 跳过
2. 产出物文件存在且有效？→ 标记完成，跳过
3. 否则 → 执行该阶段

---

## 阶段执行

### Phase 1: 需求收集 (demand)

**触发条件**: `outputs/01_demand/demand.json` 不存在

**执行步骤**:
1. 与用户对话，收集：业务目标、现有项目路径、技术约束
2. 运行 `scripts/01_demand_collect.py`
3. 生成 `outputs/01_demand/demand.json`

**完成检查**:
- [ ] JSON 文件存在
- [ ] 包含 `keywords` 和 `constraints` 字段

**完成后**: → Phase 2

---

### Phase 2: 仓库搜索 (search)

**触发条件**: `outputs/02_candidates/candidates.json` 不存在

**可跳过**: 如果 `config.target_repos` 已预设目标仓库

**执行步骤**:
1. 读取 `outputs/01_demand/demand.json`
2. 运行 `scripts/02_repo_search.py`
3. 生成 `outputs/02_candidates/candidates.json`

**完成检查**:
- [ ] 至少 3 个候选仓库

**完成后**: → Phase 3

---

### Phase 3: 仓库分析 (analyze)

**触发条件**: `outputs/03_analysis/structures/` 下无 JSON 文件

**加载 Skill**: `skills/repo-analyzer`

**执行步骤**:
1. 克隆候选仓库: `scripts/clone_repos.ps1`
2. **优先读取 AI 指令文件**: `AGENTS.md`、`CLAUDE.md`
3. AST 结构分析: `scripts/analyze_repo.py`
4. 可选 gitingest: `scripts/gitingest_all.ps1`

**完成检查**:
- [ ] `outputs/03_analysis/structures/*.json` 存在
- [ ] `outputs/03_analysis/cloned/` 有克隆的仓库

**完成后**: → Phase 4

---

### Phase 4: 依赖图 (depgraph)

**触发条件**: `outputs/04_depgraph/` 下无 JSON 文件

**加载 Skill**: `skills/dep-graph`

**执行步骤**:
1. 对每个 structure.json 运行 `scripts/build_dep_graph.py`
2. 查看 communities、leaf_nodes、hub_nodes
3. 确定提取候选

**完成检查**:
- [ ] `outputs/04_depgraph/*.json` 存在
- [ ] JSON 包含 `nodes` 和 `communities`

**完成后**: → Phase 5

---

### Phase 5: 模块提取 (extract)

**触发条件**: 无已提取或已安装的模块

**加载 Skill**: `skills/module-extractor`

**决策点**: 安装型 vs 提取型（见 skill 的决策树）

**安装型执行**:
1. `pip install <package>`
2. 在 `06_module_market/python/modules/<project>/<feature>/` 创建 router.py
3. router.py 100% 调用源库 API

**提取型执行**:
1. `scripts/extract_feature_module.py --preview` 确认文件列表
2. 去掉 `--preview` 实际提取
3. 检查 `outputs/05_modules/extracted_modules/`

**完成检查**:
- [ ] 模块目录存在（05_modules 或 06_module_market/python/modules）

**完成后**: → Phase 6

---

### Phase 6: 模块上架 (market)

**触发条件**: 无验证脚本或验证未通过

**加载 Skill**: `skills/module-demo-builder`

**五步走 — 读 → 试 → 验 → 评 → 拿**:

**a. 读 — moduleContent + seed 元数据**:
1. seed-modules.ts 写好元数据
2. `_components/constants.tsx` 添加 `moduleContent`（problem / fitCriteria）

**b. 试 — router + demo endpoint**:
1. router.py 实现核心 API（100% 调用源库）
2. main.py 挂载路由
3. seed-modules.ts 设置 `demoEndpoint` + `demoPayload`

**c. 验 — verify script + /verify endpoint**:
1. 生成 `python/workflows/verify_<module>.py`
2. 设计 3+ 组对比用例，**运行 PASS 才继续**
3. router.py 添加 `/verify` 端点

**d. 评 — evaluation record（基于实际运行结果）**:
1. 运行验证，保存结果到 `python/results/eval_<module>.json`
2. 记录分数、pass/fail、耗时、结论（可用/有风险/不可用）
3. 前端展示评估报告
4. **只有结论为"可用"才标记 status: active**

**e. 拿 — installation guide**:
1. 前端展示安装命令 + 源码链接

**完成检查**:
- [ ] 验证脚本全部 PASS
- [ ] `python/results/eval_<module>.json` 存在
- [ ] 前端 5 个 tab 可用

---

## 状态管理

### 查看状态

```
/repo-reuse status
```

显示：
```
Repo Reuse Flow — textbook-rag
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 1. 需求收集    2026-03-28
✅ 2. 仓库搜索    2026-03-28
✅ 3. 仓库分析    2026-03-29
✅ 4. 依赖图      2026-03-29
🔄 5. 模块提取    ← 当前
⏳ 6. 模块上架
```

### 快捷方式

| 命令 | 说明 |
|------|------|
| `/repo-reuse` | 启动/继续 |
| `/repo-reuse goto extract` | 跳到提取阶段 |
| `/repo-reuse skip` | 跳过当前阶段 |
| `/repo-reuse reset` | 重新开始 |
