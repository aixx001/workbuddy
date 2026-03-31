# Repo Reuse Flow

开源项目筛选→分析→模块提取→落地复用 全流程工作流

## 功能特点

- 🔍 **智能搜索**: 根据需求自动生成关键词，搜索GitHub高质量仓库
- 📊 **深度分析**: 分析仓库结构、依赖、代码规模、许可证兼容性
- 🏆 **自动评分**: 多维度量化评分，帮助选择最优仓库
- 🔧 **模块提取**: 自动识别核心模块，解耦清理
- 📄 **方案生成**: 输出完整的集成文档和落地步骤

## 快速开始

### 1. 安装依赖

```bash
pip install requests beautifulsoup4
```

### 2. 运行完整流程

```bash
python scripts/run_workflow.py --project-path "C:/my-project"
```

### 3. 分阶段运行

```bash
# 阶段1: 收集需求
python scripts/01_demand_collect.py

# 阶段2: 搜索仓库
python scripts/02_repo_search.py --keywords "FastAPI JWT"

# 阶段3: 分析仓库
python scripts/03_repo_analyze.py

# 阶段4: 敲定仓库
python scripts/04_repo_select.py

# 阶段5: 提取模块
python scripts/05_module_extract.py

# 阶段6: 生成方案
python scripts/06_integration_generate.py
```

## 工作流程

```
需求收集 → GitHub搜索 → 仓库分析 → 最优敲定 → 模块提取 → 集成方案
   ↓           ↓           ↓          ↓          ↓         ↓
 demand.json  candidates  analysis   final     modules   plan.md
              .json       .json      repo      .json
```

## 目录结构

```
repo-reuse-flow/
├── SKILL.md                    # Skill说明文件
├── README.md                   # 本文件
├── scripts/
│   ├── run_workflow.py         # 主入口脚本
│   ├── 01_demand_collect.py    # 需求收集
│   ├── 02_repo_search.py       # 仓库搜索
│   ├── 03_repo_analyze.py      # 仓库分析
│   ├── 04_repo_select.py       # 仓库敲定
│   ├── 05_module_extract.py    # 模块提取
│   └── 06_integration_generate.py  # 方案生成
├── references/
│   ├── github_search_guide.md  # GitHub搜索技巧
│   ├── license_guide.md        # 许可证指南
│   └── scoring_template.md     # 打分模板
└── config/
    └── settings.json            # 配置文件
```

## 配置

编辑 `config/settings.json`:

```json
{
    "github_token": "your_token_here",
    "min_stars": 100,
    "max_candidates": 10,
    "required_licenses": ["MIT", "Apache-2.0", "BSD-3-Clause"]
}
```

## 输出示例

```
outputs/
├── 01_demand/
│   └── demand.json           # 结构化需求文档
├── 02_candidates/
│   └── candidates.json       # 候选仓库列表
├── 03_analysis/
│   └── analysis_report.json  # 详细分析报告
├── 04_selected/
│   └── final_repo.json       # 最终选择
├── 05_modules/
│   └── extracted_modules/
│       └── modules_report.json  # 模块报告
└── 06_integration/
    ├── integration_plan.json  # JSON方案
    └── integration_plan.md    # Markdown方案
```

## 许可证

MIT License
