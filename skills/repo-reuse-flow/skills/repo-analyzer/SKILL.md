---
name: repo-analyzer
description: |
  Static AST analysis of Python repositories without pip install.
  Use when analyzing external/unfamiliar repos where installing dependencies is impractical.
  Extracts classes, functions, signatures, inheritance chains, and import relationships.
  Triggers: AST分析, 仓库分析, 结构分析, analyze repo, 代码结构
description_zh: "纯静态 AST 分析外部 Python 仓库"
description_en: "Static AST analysis of external Python repos"
---

# Repo Analyzer

> **核心问题**: 如何在不安装目标包的情况下，理解一个陌生仓库的结构？

## 方法论

用 Python `ast` 模块做纯静态分析，零运行时依赖。

### 分析优先级

```
1. 先读 AI 指令文件（信号密度最高）
   └─ AGENTS.md / CLAUDE.md / CONTRIBUTING.md

2. 再跑 AST 结构分析
   └─ scripts/analyze_repo.py → *_structure.json

3. 可选 gitingest 生成摘要
   └─ scripts/gitingest_all.ps1 → *_digest.txt
```

### AI 指令文件

很多主流项目自带 AI 理解指令（如 langchain 有 `AGENTS.md` + `CLAUDE.md`），
这是项目维护者专门为 AI 编写的架构说明，**信号密度极高，应优先读取**。

### AST 提取内容

| 维度 | 提取内容 |
|------|----------|
| 结构 | 类定义、函数/方法签名、装饰器 |
| 关系 | import 语句、继承链、模块间依赖 |
| 度量 | 文件行数、类数量、函数数量 |

### 反模式

| 工具 | 为什么不用 |
|------|----------|
| `pydeps` | 需要 pip install，无法分析未安装的外部仓库 |
| `Tach` | 面向自己项目的边界管理，不适合拆解外部代码 |
| `importlab` | 依赖运行时 import 解析 |

## 使用

```bash
cd c:/Users/40270/.workbuddy/skills/repo-reuse-flow

# 分析单个仓库
.venv\Scripts\python.exe skills/repo-analyzer/scripts/analyze_repo.py /path/to/cloned/repo \
  -o outputs/03_analysis/structures/repo_structure.json

# 批量克隆 + 分析
skills/repo-analyzer/scripts/clone_repos.ps1 -Repos "owner/repo1","owner/repo2"
skills/repo-analyzer/scripts/gitingest_all.ps1
```

## 输出

`*_structure.json` 包含：
- `files` — 每个 .py 文件的类/函数/import 列表
- `summary` — 统计信息（总文件数、总类数、总函数数）

## 脚本

| 脚本 | 作用 |
|------|------|
| `scripts/analyze_repo.py` | 核心 AST 分析（本 skill 目录下） |
| `scripts/clone_repos.ps1` | 克隆仓库 |
| `scripts/gitingest_all.ps1` | 批量 gitingest 摘要 |
