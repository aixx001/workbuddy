---
name: module-demo-builder
description: |
  Build demos and contrastive verification for Module Market modules. Two steps:
  Step 1: Generate verification script (workflows/verify_*.py) with 3+ contrastive test cases
  Step 2: Wire up frontend demo (router.py endpoint + page.tsx diagnostic report UI)
  Triggers: 生成演示, 模块演示, demo, 验证脚本, verify, 接入demo, 模块上架
description_zh: "为模块市场生成验证脚本和前端演示"
description_en: "Build verification scripts and frontend demos for modules"
---

# Module Demo Builder

为 Module Market 的每个模块生成「一看就懂」的演示和「一键验证」的测试。

## 核心目标

> 用户看到演示页面，一眼就能判断："对，这就是我想要的工具。"

## 两步流程

```
Step 1: 验证脚本                    Step 2: 前端演示
┌───────────────────┐             ┌───────────────────┐
│ verify_*.py       │             │ router.py 端点     │
│ ├─ 3+ 组对比用例    │   ──→      │ page.tsx UI       │
│ ├─ 期望分数断言     │             │ ├─ 诊断报告面板     │
│ └─ CLI 可独立运行   │             │ └─ 一键对比验证     │
└───────────────────┘             └───────────────────┘
```

---

## Step 1: 生成验证脚本

**目标**: 创建 `python/workflows/verify_<module_slug>.py`，证明模块能正确区分好坏输入。

### 1.1 分析模块能力

先读取模块的 `router.py` 和 `meta.json`，理解：
- 模块做什么（评估？生成？检索？）
- 输入输出格式（EvalRequest → EvalResponse）
- 哪些 API 端点可用

### 1.2 设计对比用例

**必须设计 3+ 组对比用例**，每组包含：

| 字段 | 说明 |
|------|------|
| `label` | 用例名（如 "✅ 忠实回答"） |
| `type` | 用例类型（如 `faithful`、`hallucinated`、`off_topic`） |
| `input` | 模块的输入数据 |
| `expected` | 期望结果的断言条件 |

**对比用例设计原则**：
1. **必须有正例和反例** — 不能只测"好"的情况
2. **差异要明显** — 正例和反例的差距要大到机器和人类都能分辨
3. **场景要直觉** — 用户看到用例名就知道在测什么
4. **用中文场景** — 贴近目标用户的使用环境

### 1.3 脚本模板

```python
#!/usr/bin/env python3
"""
verify_<module_slug>.py — Contrastive verification for <Module Name>

Tests the module's ability to distinguish good vs bad inputs
using 3+ contrastive test cases.

Usage:
    python workflows/verify_<module_slug>.py

Prerequisites:
    uvicorn main:app --reload --port 8100
"""

import httpx
import json
import time
import sys
from tabulate import tabulate

# ============================================================
# 配置常量
# Configuration Constants
# ============================================================

API_BASE = "http://localhost:8100"
ENDPOINT = "/demo/<project>/<module>/quick"
TIMEOUT_SECONDS = 120

# ============================================================
# 对比用例定义
# Contrastive Test Case Definitions
# ============================================================

# 每组用例包含: 标签、类型、请求体、断言条件
# Each case contains: label, type, payload, assertion
CASES = [
    {
        "label": "✅ 正例描述",
        "type": "positive",
        "payload": { ... },           # API 请求体
        "check": lambda scores: ...,  # 断言条件
    },
    {
        "label": "❌ 反例描述",
        "type": "negative",
        "payload": { ... },
        "check": lambda scores: ...,
    },
    # ... 至少 3 组
]

# ============================================================
# 步骤 1：逐一执行对比用例
# Step 1: Run contrastive test cases
# ============================================================

results = []
for case in CASES:
    # 发送请求并计时
    # Send request and measure elapsed time
    start = time.time()
    resp = httpx.post(
        f"{API_BASE}{ENDPOINT}",
        json=case["payload"],
        timeout=TIMEOUT_SECONDS,
    )
    data = resp.json()
    elapsed = round(time.time() - start, 2)

    # 检查断言条件
    # Check assertion condition
    passed = case["check"](data.get("scores", {}))
    results.append({
        "label": case["label"],
        "type": case["type"],
        "scores": data.get("scores", {}),
        "elapsed": elapsed,
        "passed": passed,
    })

    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} | {case['label']} | {elapsed}s")

# ============================================================
# 步骤 2：汇总结果
# Step 2: Summarize results
# ============================================================

print()
result_table = tabulate(
    [
        [r["label"], r["type"],
         "PASS" if r["passed"] else "FAIL",
         f"{r['elapsed']}s",
         json.dumps(r["scores"], ensure_ascii=False)]
        for r in results
    ],
    headers=["用例 Case", "类型 Type", "结果 Result", "耗时 Time", "分数 Scores"],
    tablefmt="simple",
)
print(result_table)

# 总结
# Summary
all_passed = all(r["passed"] for r in results)
print(f"\n{'=' * 60}")
print(f"{'🎉 ALL PASSED' if all_passed else '⚠️ SOME FAILED'}")
print(f"{'=' * 60}")
sys.exit(0 if all_passed else 1)
```

### 1.4 验证脚本必须通过

```bash
cd outputs/06_module_market/python
python workflows/verify_<module_slug>.py
# 预期: 全部 PASS，退出码 0
```

---

## Step 2: 接入前端演示

**目标**: 让用户在浏览器里一眼看懂模块价值。

### 2.1 后端：添加 /verify 端点

在模块的 `router.py` 中添加验证端点：

```python
@router.post("/<module>/verify")
async def run_verification():
    """一键对比验证 — N 组用例测试区分度"""
    # 复用 Step 1 的 CASES，逐一调用评估逻辑
    # 返回 VerifyResponse(cases=[], all_passed=bool, ...)
```

### 2.2 前端：诊断报告式结果

**结果展示必须回答三个问题**：
1. **总体如何？** — 诊断总览（综合评分 + 一句话结论）
2. **每个维度怎样？** — 每个指标的分数 + 自然语言解读
3. **用什么模型、花了多久？** — 技术细节

**诊断报告结构**：
```
┌─────────────────────────────────────────────┐
│ ✅ 诊断结果                           85分  │
│ 回答质量优秀 — 忠于文档、切题、检索精准      │
├─────────────────────────────────────────────┤
│ 🔍 幻觉检测                    ✅ 100%     │
│ ████████████████████████████████            │
│ 回答完全基于检索到的文档，没有编造内容        │
├─────────────────────────────────────────────┤
│ 🎯 是否切题                    ✅ 78%      │
│ ████████████████████████                    │
│ 回答直接回应了用户的问题，表述精准            │
├─────────────────────────────────────────────┤
│ 📚 文档相关性                   ⚠️ 45%     │
│ ██████████████                              │
│ 检索到的文档相关性一般，可能混入了噪声        │
├─────────────────────────────────────────────┤
│ ⏱ 耗时 8.89s · 模型: gpt-4o-mini           │
└─────────────────────────────────────────────┘
```

### 2.3 前端：一键对比验证

在 sidebar 的"验"tab 中：
- 一个按钮触发 `/verify` 端点
- 结果显示每个用例的 Pass/Fail
- 总览栏显示"全部通过"或"部分未通过"

### 2.4 需要修改的文件

| 文件 | 改动 |
|------|------|
| `python/modules/<project>/<module>/router.py` | 添加 `/verify` 端点 |
| `payload/src/app/(frontend)/_components/constants.tsx` | 添加模块的 `moduleContent` + `evaluationRecords` + `verifyEndpoints` |
| `payload/src/seed/seed-modules.ts` | 设置 `demoEndpoint` + `demoPayload` |

---

## 质量标准

### Demo 必须满足的标准

- [ ] 用户看到结果，**3 秒内**能理解这个模块做什么
- [ ] 结果不是一堆 JSON 数字，而是**自然语言诊断**
- [ ] 每个分数都有**直觉解读**（"没有瞎编" vs "0.95"）
- [ ] 有**正反对比**让用户知道"好"和"坏"的区别

### 验证脚本必须满足的标准

- [ ] CLI 可独立运行，不依赖前端
- [ ] 3+ 组对比用例，覆盖正例和反例
- [ ] 所有用例全部 PASS
- [ ] 退出码：0 = 全部通过，1 = 有失败

---

## 已完成的模块

| 模块 | 验证脚本 | 前端演示 | 状态 |
|------|----------|----------|------|
| ragas-evaluation | `verify_ragas_evaluation.py` | 读/试/验/评/拿 全部接入 | ✅ |
| deepeval | `verify_deepeval.py` | 读/试/验/评/拿 全部接入 | ✅ |
| dspy-signatures | `verify_dspy_signatures.py` | 读/试/验/评/拿 全部接入 | ✅ |
| promptfoo | `verify_promptfoo.py` | 读/试/验/评/拿 全部接入 | ✅ |
| ragas-testset | `verify_ragas_testset.py` | 读/试/验/评/拿 全部接入 | ✅ |
| ragas-prompt | `verify_ragas_prompt.py` | 读/试/验/评/拿 全部接入 | ✅ |

## 参考文件

- 验证脚本模板: `python/workflows/verify_ragas_evaluation.py`
- 后端 router 模板: `python/modules/ragas/evaluation/router.py`
- 前端入口: `payload/src/app/(frontend)/page.tsx` (45行路由 shell)
- 前端组件目录: `payload/src/app/(frontend)/_components/`
  - `constants.tsx` — 类型、常量、moduleContent、evaluationRecords
  - `hooks.ts` — useModuleData / useSidebarResize / useCopyToClipboard / useUrlRouting
  - `tabs/ReadTab.tsx` — ① 读
  - `tabs/TryTab.tsx` — ② 试（最复杂，~250行）
  - `tabs/VerifyTab.tsx` — ③ 验
  - `tabs/EvalTab.tsx` — ④ 评
  - `tabs/TakeTab.tsx` — ⑤ 拿
  - `ModuleListPage.tsx` / `ModuleDetailPage.tsx`
  - `Sidebar.tsx` / `DetailSidebar.tsx`
  - `ProjectGroup.tsx` / `ModuleCard.tsx`
- 评估结果目录: `python/results/` (唯一数据输出)
