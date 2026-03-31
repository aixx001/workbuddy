---
name: module-extractor
description: |
  Extract or install modules from analyzed repos. Decision tree: if extracting a
  sub-module pulls in >50% of repo files, use install-type (pip install + thin API wrapper).
  Otherwise use extract-type (copy code + rewrite imports with rope).
  Triggers: 模块提取, 安装型, 提取型, extract module, 代码提取, 代码移植
description_zh: "从分析过的仓库中提取或安装模块"
description_en: "Extract or install modules from analyzed repos"
---

# Module Extractor

> **核心问题**: 这个模块应该"安装"还是"提取"？

## 决策树

```
python extract_feature_module.py --repo <path> --entry <module> --preview
                │
                ├─ 拉进了 >50% 的仓库文件？
                │    │
                │    └─ 安装型 (install)
                │       pip install + 薄壳 router.py
                │       适用: ragas, deepeval, dspy
                │
                └─ 拉进了 <50% 的文件？
                     │
                     └─ 提取型 (extract)
                        代码复制 + import 重写
                        适用: 松耦合工具库
```

## 方式 A: 安装型

适用于紧耦合框架 — 内部模块间依赖太深，提取子模块等于复制大半个库。

### 原则

1. **100% 源库 API** — router.py 只做 HTTP 包装，核心逻辑全部调用原始开源库
2. **溯源清晰** — meta.json 记录来源项目、repo URL、license、使用的 API
3. **独立可迁移** — 每个模块目录可以整体复制到目标项目

### 目录组织

```
outputs/06_module_market/python/modules/
└── <project>/              # 来源项目名 (如 ragas)
    ├── meta.json           # 项目级元数据
    └── <feature>/          # 功能模块 (如 evaluation)
        ├── meta.json       # 模块元数据
        └── router.py       # FastAPI 路由（100% 调源库 API）
```

### 操作

```bash
# 1. 安装源库
pip install ragas

# 2. 创建模块目录
mkdir -p outputs/06_module_market/python/modules/ragas/evaluation

# 3. 写 router.py — 只做 HTTP 包装
# 4. 写 meta.json — 记录溯源
```

## 方式 B: 提取型

适用于松耦合工具库 — 模块间依赖少，可以干净拆出来。

### 两种提取脚本

| 脚本 | 策略 | 适用 |
|------|------|------|
| `05_module_extract.py` | Louvain 社区检测，盲提取 | 不确定要什么 |
| `extract_feature_module.py` | 指定入口递归追踪 import | 知道要什么功能 |

### 需求驱动提取

```bash
# 预览：看会拉进多少文件
python extract_feature_module.py \
    --repo outputs/03_analysis/cloned/ragas/src/ragas \
    --entry metrics evaluation.py \
    --name evaluation --preview

# 实际提取
python extract_feature_module.py \
    --repo outputs/03_analysis/cloned/ragas/src/ragas \
    --entry metrics evaluation.py \
    --name evaluation
```

### 提取后结构

```
outputs/05_modules/extracted_modules/<module_name>/
├── __init__.py          # 自动生成
├── metrics/             # 保留原始目录结构
├── prompt/
├── manifest.json        # 模块元数据 + 溯源
├── requirements.txt     # 外部 pip 依赖
└── README.md            # 使用说明
```

## 发布到 CMS

提取/安装完成后，用 `scripts/06_module_publish.py` 发布到 Payload CMS：

```bash
# 预览
python scripts/06_module_publish.py --module ragflow_common --preview

# 导出 JSON
python scripts/06_module_publish.py --module ragflow_common --export-json
```

## 脚本

| 脚本 | 作用 |
|------|------|
| `scripts/05_module_extract.py` | Louvain 社区提取 |
| `scripts/extract_feature_module.py` | 需求驱动提取 |
| `scripts/06_module_publish.py` | 发布到 CMS |
