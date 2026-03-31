---
name: repo-reuse-flow
description: |
  Orchestrates the full pipeline of finding, analyzing, and extracting reusable modules
  from open-source GitHub repositories. 6 phases: demand → search → analyze → depgraph →
  extract → market. Each phase backed by a dedicated skill with its own methodology.
  Triggers: 开源复用, 模块提取, repo分析, 代码移植, 找开源库, github筛选, 依赖图
description_zh: "从开源仓库科学提取可复用模块的完整工作流"
description_en: "Extract reusable modules from open-source repos scientifically"
---

# Repo Reuse Flow

从别人的开源仓库中，科学地提取可复用模块，集成到自己的项目。

> **关键原则**: 分析外部仓库必须用纯静态方法（AST），不依赖 pip install。

## 使用

```
/repo-reuse                # 启动/继续流程
/repo-reuse status         # 查看进度
/repo-reuse goto analyze   # 跳转到指定阶段
/repo-reuse skip           # 跳过当前阶段
```

## 阶段

| # | 阶段 | Skill | 核心问题 |
|---|------|-------|----------|
| 1 | 需求收集 | — | 你要解决什么问题？ |
| 2 | 仓库搜索 | — | 哪个开源项目最值得借鉴？ |
| 3 | 仓库分析 | `repo-analyzer` | 不装包怎么理解它的结构？ |
| 4 | 依赖图 | `dep-graph` | 哪些模块可以安全拆出来？ |
| 5 | 模块提取 | `module-extractor` | 这个模块该安装还是提取？ |
| 6 | 模块上架 | `module-demo-builder` | 读→试→验→评→拿，全部完成才算上架 |

详见 `workflow.md` 和 `steps/step-*.md`。

## 快速开始

```bash
cd c:/Users/40270/.workbuddy/skills/repo-reuse-flow

# 单独使用某个阶段的脚本
.venv\Scripts\python.exe skills/repo-analyzer/scripts/analyze_repo.py /path/to/repo -o out.json
.venv\Scripts\python.exe skills/dep-graph/scripts/build_dep_graph.py structure.json -o depgraph.json
```

## 目录结构

```
repo-reuse-flow/
├── SKILL.md                  # ← 你在这里
├── workflow.md               # 编排：状态机 + 阶段串联
├── state-template.yaml       # 状态：6 阶段进度跟踪
├── steps/                    # 每阶段的执行步骤
├── skills/                   # 独立 skill（各有方法论）
│   ├── repo-analyzer/        #   AST 分析
│   ├── dep-graph/            #   依赖图
│   ├── module-extractor/     #   提取 vs 安装
│   └── module-demo-builder/  #   验证 + 演示
├── scripts/                  # 工具脚本
├── references/               # 参考文档
├── config/
└── outputs/                  # 各阶段产出
```
