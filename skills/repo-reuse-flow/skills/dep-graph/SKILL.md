---
name: dep-graph
description: |
  Build file-level dependency graphs from AST analysis results using NetworkX.
  Automatically detect module boundaries via Louvain community detection.
  Calculate reuse scores and identify leaf/hub nodes for extraction planning.
  Triggers: 依赖图, 模块检测, 社区检测, depgraph, module boundary, 复用性评分
description_zh: "从 AST 数据构建依赖图，自动检测模块边界"
description_en: "Build dependency graphs, detect module boundaries"
---

# Dep Graph

> **核心问题**: 哪些文件可以被安全地单独提取？哪些是核心枢纽？

## 方法论

### 三步走

```
1. 构图 — 从 import 语句构建 file→file 有向图
         (区分内部依赖 vs 外部依赖，只关注内部)

2. 检测 — Louvain 社区检测自动发现模块边界
         (同一社区的文件高度耦合，不同社区松耦合)

3. 评分 — 计算每个文件的复用价值
         (被依赖多 + 自身依赖少 = 高复用价值)
```

### 关键指标

| 指标 | 公式 | 含义 | 行动 |
|------|------|------|------|
| `reuse_score` | in / (in + out) | 复用价值 | 高分 → 值得提取 |
| `leaf_node` | out_degree == 0 | 零内部依赖 | 最容易单独提取 |
| `hub_node` | in_degree Top 5% | 核心枢纽 | 不建议单独提取 |

### 决策指南

```
reuse_score > 0.7 + leaf_node  → 🟢 提取首选
reuse_score > 0.5              → 🟡 可以提取，需检查依赖链
reuse_score < 0.3              → 🔴 依赖太多，考虑安装型
hub_node                       → ⛔ 核心枢纽，不建议单独拆
```

## 使用

```bash
cd c:/Users/40270/.workbuddy/skills/repo-reuse-flow

.venv\Scripts\python.exe skills/dep-graph/scripts/build_dep_graph.py \
  outputs/03_analysis/structures/repo_structure.json \
  -o outputs/04_depgraph/repo_depgraph.json
```

## 输出格式

```json
{
  "nodes": {
    "core/retrievers.py": {
      "in_degree": 12,
      "out_degree": 3,
      "external_deps": ["pydantic"],
      "classes": ["BaseRetriever"],
      "reuse_score": 0.85
    }
  },
  "communities": {
    "0": ["retrievers.py", "stores.py"],
    "1": ["callbacks/base.py", "callbacks/manager.py"]
  },
  "leaf_nodes": ["rate_limiters.py"],
  "hub_nodes": ["callbacks/manager.py"]
}
```

## 脚本

| 脚本 | 作用 |
|------|------|
| `scripts/build_dep_graph.py` | 构图 + 社区检测 + 评分 |

## 依赖

- `networkx` — 图算法
- `python-louvain` (community) — 社区检测
