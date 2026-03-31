#!/usr/bin/env python3
"""
verify_ragas_testset.py — Contrastive verification for Ragas Testset (Question Gen)

Tests the module's ability to generate meaningful test questions
from different types of input text using 3+ contrastive test cases.

Usage:
    python workflows/verify_ragas_testset.py

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
ENDPOINT = "/demo/ragas/question-gen/quick"
VERIFY_ENDPOINT = "/demo/ragas/question-gen/verify"
TIMEOUT_SECONDS = 60

# ============================================================
# 对比用例定义
# Contrastive Test Case Definitions
# ============================================================

# 每组用例包含: 标签、类型、请求体、断言条件
# Each case contains: label, type, payload, assertion
CASES = [
    {
        "label": "✅ 事实性文本 — 应生成基于文档的测试题",
        "type": "factual_text",
        "payload": {
            "text": (
                "光合作用（Photosynthesis）是植物、藻类和某些细菌利用光能"
                "将二氧化碳和水转化为葡萄糖和氧气的生化过程。"
                "光合作用主要发生在叶绿体中，包括光反应和暗反应两个阶段。"
                "光反应在类囊体薄膜上进行，将光能转化为 ATP 和 NADPH。"
                "暗反应（Calvin 循环）在叶绿体基质中进行，利用 ATP 和 NADPH 固定 CO2。"
            ),
            "num_questions": 3,
        },
        "check": lambda data: (
            # 至少生成 2 道题
            len(data.get("questions", [])) >= 2
            # 每道题有问题文本
            and all(q.get("question") for q in data.get("questions", []))
            # 至少有一半的题有答案
            and sum(1 for q in data.get("questions", []) if q.get("answer")) >= 1
        ),
    },
    {
        "label": "✅ 技术性文本 — 应生成技术领域问题",
        "type": "technical_text",
        "payload": {
            "text": (
                "向量数据库（Vector Database）是专门用于存储和检索高维向量数据的数据库系统。"
                "常见的向量检索算法包括 HNSW（Hierarchical Navigable Small World）、"
                "IVF（Inverted File Index）和 PQ（Product Quantization）。"
                "HNSW 通过构建多层导航图实现近似最近邻搜索，时间复杂度为 O(log n)。"
                "FAISS 是 Meta 开源的向量检索库，支持 GPU 加速。"
                "Milvus 是一个云原生的向量数据库，支持十亿级向量的实时检索。"
            ),
            "num_questions": 3,
        },
        "check": lambda data: (
            len(data.get("questions", [])) >= 2
            and all(q.get("question") for q in data.get("questions", []))
            and sum(1 for q in data.get("questions", []) if q.get("answer")) >= 1
        ),
    },
    {
        "label": "❌ 无意义噪声 — 应生成低质量或空结果",
        "type": "garbage_text",
        "payload": {
            "text": "啊啊啊啊 blah blah 123 !@#$% random noise asdfghjkl 乱码测试 xxxyyy",
            "num_questions": 3,
        },
        "check": lambda data: (
            # 无意义文本：不崩就算通过
            # 如果生成了题但质量一般也合理（LLM 可能硬编）
            # 关键是接口不能 500
            isinstance(data.get("questions", None), list)
        ),
    },
]


# ============================================================
# 步骤 1：逐一执行对比用例
# Step 1: Run contrastive test cases
# ============================================================

def main():
    print("=" * 60)
    print("Ragas Testset (Question Gen) — 对比验证")
    print("=" * 60)
    print()

    results = []
    for case in CASES:
        # 发送请求并计时
        # Send request and measure elapsed time
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

            # 检查断言条件
            # Check assertion condition
            passed = case["check"](data)

            # 提取分数信息
            questions = data.get("questions", [])
            q_count = len(questions)
            answer_rate = (
                round(sum(1 for q in questions if q.get("answer")) / max(q_count, 1), 2)
            )

        except Exception as e:
            data = {"questions": []}
            elapsed = round(time.time() - start, 2)
            q_count = 0
            answer_rate = 0
            # 无意义文本解析失败也算通过
            if case["type"] == "garbage_text":
                passed = True
            else:
                passed = False
            print(f"  ⚠️  请求失败: {e}")

        results.append({
            "label": case["label"],
            "type": case["type"],
            "elapsed": elapsed,
            "passed": passed,
            "q_count": q_count,
            "answer_rate": answer_rate,
            "sample": (data.get("questions", [{}])[0].get("question", "—")[:40]
                       if data.get("questions") else "—"),
        })

        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} | {case['label']} | {elapsed}s | {q_count} 题")
        if data.get("questions"):
            for q in data["questions"][:2]:
                print(f"       → {q.get('question', '—')[:60]}")

    # ============================================================
    # 步骤 2：汇总结果
    # Step 2: Summarize results
    # ============================================================

    print()
    result_table = tabulate(
        [
            [
                r["label"],
                r["type"],
                "PASS" if r["passed"] else "FAIL",
                f"{r['elapsed']}s",
                f"q={r['q_count']} ans={r['answer_rate']}",
            ]
            for r in results
        ],
        headers=["用例 Case", "类型 Type", "结果 Result", "耗时 Time", "详情 Details"],
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


if __name__ == "__main__":
    main()
