#!/usr/bin/env python3
"""
verify_promptfoo.py — Contrastive verification for Promptfoo Config Gen

Tests the module's ability to generate valid, correct promptfoo YAML configs
using 3+ contrastive test cases.

Usage:
    python workflows/verify_promptfoo.py

Prerequisites:
    uvicorn main:app --reload --port 8100
"""

import httpx
import json
import sys
import time
import yaml

from tabulate import tabulate

# ============================================================
# 配置常量
# Configuration Constants
# ============================================================

API_BASE = "http://localhost:8100"
ENDPOINT = "/demo/promptfoo/generate-config"
VERIFY_ENDPOINT = "/demo/promptfoo/generate-config/verify"
TIMEOUT_SECONDS = 30

# ============================================================
# 对比用例定义
# Contrastive Test Case Definitions
# ============================================================

# 每组用例包含: 标签、类型、请求体、断言条件
# Each case contains: label, type, payload, assertion
CASES = [
    {
        "label": "✅ 完整配置 — 多模型 + 多用例 + 断言",
        "type": "complete",
        "payload": {
            "prompt_template": "你是一个教育助手。根据上下文回答问题。\n上下文: {{context}}\n问题: {{question}}",
            "test_cases": [
                {
                    "question": "什么是光合作用？",
                    "expected_keywords": ["光能", "植物", "二氧化碳"],
                    "context": "光合作用是植物利用光能将CO2和H2O转化为有机物的过程。",
                },
                {
                    "question": "牛顿第三定律是什么？",
                    "expected_keywords": ["作用力", "反作用力"],
                    "context": "牛顿第三定律：两个物体之间的作用力和反作用力大小相等、方向相反。",
                },
            ],
            "models": ["openai:gpt-4o-mini", "openai:gpt-3.5-turbo"],
        },
        "check": lambda data: (
            # YAML 有效
            _is_valid_yaml(data.get("yaml_config", ""))
            # 有 2 个测试用例
            and len(data.get("config_dict", {}).get("tests", [])) == 2
            # 有 2 个 provider
            and len(data.get("config_dict", {}).get("providers", [])) == 2
            # 第一个用例有断言
            and len(data.get("config_dict", {}).get("tests", [{}])[0].get("assert", [])) > 0
            # 有运行命令
            and "promptfoo" in data.get("run_command", "")
        ),
    },
    {
        "label": "✅ 最小配置 — 空用例自动补默认",
        "type": "minimal",
        "payload": {
            "prompt_template": "回答问题：{{question}}",
            "test_cases": [],
            "models": ["openai:gpt-4o-mini"],
        },
        "check": lambda data: (
            # YAML 有效
            _is_valid_yaml(data.get("yaml_config", ""))
            # 空用例时应自动补一个示例
            and len(data.get("config_dict", {}).get("tests", [])) >= 1
            # 有 provider
            and len(data.get("config_dict", {}).get("providers", [])) >= 1
        ),
    },
    {
        "label": "✅ 中文场景 — 关键词断言正确生成",
        "type": "chinese",
        "payload": {
            "prompt_template": "你是一个中文阅读理解助手。\n原文: {{context}}\n问题: {{question}}",
            "test_cases": [
                {
                    "question": "鲁迅的代表作是什么？",
                    "expected_keywords": ["呐喊", "狂人日记"],
                    "context": "鲁迅（1881-1936），原名周树人，代表作有《呐喊》《彷徨》等。《狂人日记》是中国现代文学史上第一篇白话小说。",
                },
            ],
            "models": ["openai:gpt-4o-mini"],
        },
        "check": lambda data: (
            _is_valid_yaml(data.get("yaml_config", ""))
            # 用例中包含中文关键词断言
            and any(
                a.get("value") in ["呐喊", "狂人日记"]
                for t in data.get("config_dict", {}).get("tests", [])
                for a in t.get("assert", [])
            )
            # prompt 包含中文
            and "中文" in data.get("config_dict", {}).get("prompts", [""])[0]
        ),
    },
]


def _is_valid_yaml(yaml_str: str) -> bool:
    """检查 YAML 字符串是否合法"""
    try:
        obj = yaml.safe_load(yaml_str)
        return isinstance(obj, dict)
    except Exception:
        return False


# ============================================================
# 步骤 1：逐一执行对比用例
# Step 1: Run contrastive test cases
# ============================================================

def main():
    print("=" * 60)
    print("Promptfoo Config Gen — 对比验证")
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
        except Exception as e:
            data = {}
            elapsed = round(time.time() - start, 2)
            passed = False
            print(f"  ⚠️  请求失败: {e}")

        results.append({
            "label": case["label"],
            "type": case["type"],
            "elapsed": elapsed,
            "passed": passed,
            "tests_count": len(data.get("config_dict", {}).get("tests", [])),
            "providers_count": len(data.get("config_dict", {}).get("providers", [])),
            "yaml_valid": _is_valid_yaml(data.get("yaml_config", "")),
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
            [
                r["label"],
                r["type"],
                "PASS" if r["passed"] else "FAIL",
                f"{r['elapsed']}s",
                f"tests={r['tests_count']} providers={r['providers_count']} yaml={r['yaml_valid']}",
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
