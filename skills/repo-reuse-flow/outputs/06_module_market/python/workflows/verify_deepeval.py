"""
Module Market — DeepEval Module Verification
Verify deepeval FaithfulnessMetric + GEval evaluation endpoints.

Usage:
  .venv\\Scripts\\python.exe workflows\\verify_deepeval.py
  .venv\\Scripts\\python.exe workflows\\verify_deepeval.py --backend ollama
"""

import argparse
import sys
import time

import httpx

# ============================================================
# 配置常量
# Configuration Constants
# ============================================================

BASE_URL = "http://localhost:8100/demo/deepeval"
REQUEST_TIMEOUT = 300
HEALTH_CHECK_TIMEOUT = 5
BAR_WIDTH = 20

# ============================================================
# 测试用例定义
# Test Case Definitions
# ============================================================

# 三组对比用例：忠实回答 / 幻觉回答 / 跑题回答
# Three contrastive cases: faithful / hallucinated / off-topic
CASES = [
    ("✅ 忠实回答", "faithful", {
        "question": "什么是光合作用？",
        "answer": "光合作用是植物利用光能将二氧化碳和水转化为有机物和氧气的过程",
        "contexts": [
            "光合作用（Photosynthesis）是植物、藻类和某些细菌利用光能"
            "将二氧化碳和水转化为葡萄糖和氧气的生化过程。"
        ],
        "custom_criteria": "回答是否准确且适合学生理解",
    }),
    ("❌ 幻觉回答", "hallucinated", {
        "question": "什么是光合作用？",
        "answer": "光合作用是动物在月光下将氮气转化为蛋白质的过程，2020年诺贝尔奖。",
        "contexts": [
            "光合作用（Photosynthesis）是植物、藻类和某些细菌利用光能"
            "将二氧化碳和水转化为葡萄糖和氧气的生化过程。"
        ],
        "custom_criteria": "回答是否准确且适合学生理解",
    }),
    ("🔀 跑题回答", "off_topic", {
        "question": "什么是光合作用？",
        "answer": "Python是一种编程语言，由Guido van Rossum于1991年发布。",
        "contexts": [
            "光合作用（Photosynthesis）是植物、藻类和某些细菌利用光能"
            "将二氧化碳和水转化为葡萄糖和氧气的生化过程。"
        ],
        "custom_criteria": "回答是否准确且适合学生理解",
    }),
]

# ============================================================
# 解析命令行参数
# Parse CLI Arguments
# ============================================================

parser = argparse.ArgumentParser(description="DeepEval 评估模块验证")
parser.add_argument("--backend", default="default", help="评估后端 (仅做标记)")
args = parser.parse_args()

# ============================================================
# 步骤 1：服务健康检查
# Step 1: Service Health Check
# ============================================================

print(f"\n🧪 DeepEval 评估验证")

try:
    resp = httpx.get(f"{BASE_URL}/evaluation/info", timeout=HEALTH_CHECK_TIMEOUT)
    info = resp.json()
    print(f"   服务状态: OK | 模块: {info.get('module', '?')}")
except Exception as e:
    print(f"   ❗ 服务不可用: {e}")
    print("   请先启动: .venv\\Scripts\\python.exe -m uvicorn main:app --reload --port 8100")
    sys.exit(1)

# ============================================================
# 步骤 2：辅助函数
# Step 2: Helper Functions
# ============================================================

FAITHFULNESS_THRESHOLD = 0.5
GEVAL_THRESHOLD = 0.5


def print_scores(label, data, elapsed):
    """打印单个测试用例的评分结果
    Print scores for a single test case"""
    scores = data.get("scores", {})
    print(f"  {label}  ({elapsed}s)")
    for metric, value in scores.items():
        if value is None:
            print(f"    {metric:25s} {'░' * BAR_WIDTH} N/A")
        else:
            filled = int(value * BAR_WIDTH)
            bar = "█" * filled + "░" * (BAR_WIDTH - filled)
            print(f"    {metric:25s} {bar} {value:.4f}")

    # 打印解释
    # Print reasons
    details = data.get("details", {})
    if details.get("faithfulness_reason"):
        reason = details["faithfulness_reason"]
        print(f"    💬 faithfulness 理由: {reason[:120]}")
    if details.get("geval_reason"):
        reason = details["geval_reason"]
        print(f"    💬 GEval 理由: {reason[:120]}")
    if details.get("faithfulness_error"):
        print(f"    ⚠️  faithfulness 错误: {details['faithfulness_error'][:120]}")
    if details.get("geval_error"):
        print(f"    ⚠️  GEval 错误: {details['geval_error'][:120]}")


def check_discrimination(case_type, scores):
    """检查评分是否具有区分度
    Check if scores discriminate good vs bad answers"""
    faith = scores.get("faithfulness")
    geval = scores.get("custom_geval")

    # 至少一个有效指标
    # Need at least one valid metric
    if faith is None and geval is None:
        return False

    if case_type == "faithful":
        # 忠实回答应该得高分
        if faith is not None:
            return faith > FAITHFULNESS_THRESHOLD
        if geval is not None:
            return geval > GEVAL_THRESHOLD
    else:
        # 幻觉/跑题回答应该得低分
        if faith is not None:
            return faith < FAITHFULNESS_THRESHOLD
        if geval is not None:
            return geval < GEVAL_THRESHOLD

    return False


# ============================================================
# 步骤 3：运行三组对比测试
# Step 3: Run Three Contrastive Tests
# ============================================================

print(f"\n{'═' * 60}")
print(f"  DeepEval 评估验证 — FaithfulnessMetric + GEval")
print(f"{'═' * 60}")

passed = 0
total = len(CASES)

with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
    for label, case_type, payload in CASES:
        t0 = time.time()
        try:
            resp = client.post(f"{BASE_URL}/evaluation", json=payload)
            elapsed = round(time.time() - t0, 2)

            if resp.status_code == 200:
                data = resp.json()
                print_scores(label, data, elapsed)

                if data.get("error"):
                    print(f"    ⚠️  模块错误: {data['error'][:120]}")
                elif check_discrimination(case_type, data.get("scores", {})):
                    passed += 1
            else:
                print(f"  {label}  ❗ HTTP {resp.status_code}")
                print(f"    {resp.text[:200]}")
        except Exception as e:
            elapsed = round(time.time() - t0, 2)
            print(f"  {label}  ❗ 错误 ({elapsed}s): {e}")

# ============================================================
# 步骤 4：汇总结果
# Step 4: Summary
# ============================================================

status = "✅ PASS" if passed == total else f"⚠️  {passed}/{total}"
print(f"\n  区分度检查: {status}")

all_passed = passed == total

print(f"\n{'═' * 60}")
print(f"  {'🎉 全部通过' if all_passed else '⚠️  有失败项'}")
print(f"{'═' * 60}\n")

sys.exit(0 if all_passed else 1)
