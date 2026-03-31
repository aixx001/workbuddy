#!/usr/bin/env python3
"""
verify_ragas_prompt.py — Contrastive verification for Ragas PydanticPrompt

Tests the module's ability to render structured prompts and generate
valid structured output using 3+ contrastive test cases.

Usage:
    python workflows/verify_ragas_prompt.py

Prerequisites:
    uvicorn main:app --reload --port 8100
"""

import httpx
import json
import sys
import time

from tabulate import tabulate

# ============================================================
# 配置常量
# Configuration Constants
# ============================================================

API_BASE = "http://localhost:8100"
ENDPOINT = "/demo/ragas/prompt"
TIMEOUT_SECONDS = 60

# ============================================================
# 对比用例定义
# Contrastive Test Case Definitions
# ============================================================

CASES = [
    {
        "label": "✅ 科学主题 — 应渲染 prompt + 生成题目",
        "type": "science",
        "payload": {
            "context": (
                "光合作用（Photosynthesis）是植物、藻类和某些细菌利用光能"
                "将二氧化碳和水转化为葡萄糖和氧气的生化过程。"
                "光合作用主要发生在叶绿体中，包括光反应和暗反应两个阶段。"
            ),
            "topic": "生物学",
            "run_llm": True,
        },
        "check": lambda data: (
            # prompt 渲染成功
            len(data.get("rendered_prompt", "")) > 50
            # LLM 返回了结构化输出
            and data.get("output", {}).get("question")
            # 有难度标注
            and data.get("output", {}).get("difficulty") in ("easy", "medium", "hard")
            # schema 信息完整
            and "input_schema" in data.get("template_info", {})
        ),
    },
    {
        "label": "✅ 技术主题 — 应适配不同领域",
        "type": "technical",
        "payload": {
            "context": (
                "HNSW（Hierarchical Navigable Small World）是近似最近邻搜索算法。"
                "通过构建多层跳表结构实现 O(log n) 搜索。广泛用于 FAISS、Milvus。"
            ),
            "topic": "向量检索",
            "run_llm": True,
        },
        "check": lambda data: (
            len(data.get("rendered_prompt", "")) > 50
            and data.get("output", {}).get("question")
            and data.get("output", {}).get("difficulty") in ("easy", "medium", "hard")
        ),
    },
    {
        "label": "✅ 纯渲染 — 不调 LLM 也能看到 prompt",
        "type": "render_only",
        "payload": {
            "context": "牛顿第三定律指出，作用力与反作用力大小相等、方向相反。",
            "topic": "物理学",
            "run_llm": False,
        },
        "check": lambda data: (
            # prompt 渲染成功
            len(data.get("rendered_prompt", "")) > 50
            # 不调 LLM，output 应该是 None
            and data.get("output") is None
            # schema 信息仍然完整
            and "input_schema" in data.get("template_info", {})
            and "output_schema" in data.get("template_info", {})
        ),
    },
]


# ============================================================
# 执行验证
# ============================================================

def main():
    print("=" * 60)
    print("Ragas Prompt Framework — 对比验证")
    print("=" * 60)
    print()

    results = []
    for case in CASES:
        start = time.time()
        try:
            resp = httpx.post(
                f"{API_BASE}{ENDPOINT}",
                json=case["payload"],
                timeout=TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            data = resp.json()
            elapsed = round(time.time() - start, 2)

            passed = case["check"](data)

            prompt_len = len(data.get("rendered_prompt", ""))
            has_output = bool(data.get("output", {}).get("question")) if data.get("output") else False
            question = (data.get("output", {}) or {}).get("question", "—")[:50]

        except Exception as e:
            data = {}
            elapsed = round(time.time() - start, 2)
            passed = False
            prompt_len = 0
            has_output = False
            question = "—"
            print(f"  ⚠️  请求失败: {e}")

        results.append({
            "label": case["label"],
            "type": case["type"],
            "elapsed": elapsed,
            "passed": passed,
            "prompt_len": prompt_len,
            "has_output": has_output,
            "question": question,
        })

        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} | {case['label']} | {elapsed}s | prompt={prompt_len}chars")
        if has_output:
            print(f"       → Q: {question}")

    # 汇总
    print()
    result_table = tabulate(
        [
            [
                r["label"],
                r["type"],
                "PASS" if r["passed"] else "FAIL",
                f"{r['elapsed']}s",
                f"prompt={r['prompt_len']} output={r['has_output']}",
            ]
            for r in results
        ],
        headers=["用例 Case", "类型 Type", "结果 Result", "耗时 Time", "详情 Details"],
        tablefmt="simple",
    )
    print(result_table)

    all_passed = all(r["passed"] for r in results)
    print(f"\n{'=' * 60}")
    print(f"{'🎉 ALL PASSED' if all_passed else '⚠️ SOME FAILED'}")
    print(f"{'=' * 60}")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
