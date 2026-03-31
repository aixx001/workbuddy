"""
Module Market — Ragas Evaluation Module Verification
Verify quick (LLM-as-Judge) and full Ragas pipeline evaluation endpoints.

Usage:
  .venv\\Scripts\\python.exe workflows\\verify_ragas_evaluation.py
  .venv\\Scripts\\python.exe workflows\\verify_ragas_evaluation.py --backend ollama
  .venv\\Scripts\\python.exe workflows\\verify_ragas_evaluation.py --backend azure --full
"""

import argparse
import sys
import time

import httpx

# ============================================================
# 配置常量
# Configuration Constants
# ============================================================

BASE_URL = "http://localhost:8100/demo/ragas"
REQUEST_TIMEOUT = 300
HEALTH_CHECK_TIMEOUT = 5
FAITHFULNESS_THRESHOLD = 0.5
ALL_METRICS = ["faithfulness", "answer_relevancy", "context_precision"]
BAR_WIDTH = 20

# ============================================================
# 测试用例定义
# Test Case Definitions
# ============================================================

# 三组对比用例：忠实回答 / 幻觉回答 / 跑题回答
# Three contrastive cases: faithful / hallucinated / off-topic
CASES = [
    ("✅ 忠实回答", {
        "question": "什么是光合作用？",
        "answer": "光合作用是植物利用光能将二氧化碳和水转化为有机物和氧气的过程",
        "contexts": [
            "光合作用（Photosynthesis）是植物、藻类和某些细菌利用光能"
            "将二氧化碳和水转化为葡萄糖和氧气的生化过程。"
        ],
        "reference": "光合作用是生物体利用光能将无机物合成有机物的过程",
    }),
    ("❌ 幻觉回答", {
        "question": "什么是光合作用？",
        "answer": "光合作用是动物在月光下将氮气转化为蛋白质的过程，2020年诺贝尔奖。",
        "contexts": [
            "光合作用（Photosynthesis）是植物、藻类和某些细菌利用光能"
            "将二氧化碳和水转化为葡萄糖和氧气的生化过程。"
        ],
        "reference": "光合作用是生物体利用光能将无机物合成有机物的过程",
    }),
    ("🔀 跑题回答", {
        "question": "什么是光合作用？",
        "answer": "Python是一种编程语言，由Guido van Rossum于1991年发布。",
        "contexts": [
            "光合作用（Photosynthesis）是植物、藻类和某些细菌利用光能"
            "将二氧化碳和水转化为葡萄糖和氧气的生化过程。"
        ],
        "reference": "光合作用是生物体利用光能将无机物合成有机物的过程",
    }),
]

# ============================================================
# 解析命令行参数
# Parse CLI Arguments
# ============================================================

parser = argparse.ArgumentParser(description="Ragas 评估模块验证")
parser.add_argument("--backend", default="azure", choices=["azure", "ollama"],
                    help="评估后端 (默认: azure)")
parser.add_argument("--full", action="store_true",
                    help="同时测试完整 Ragas 管道 (较慢, 15-60s/case)")
args = parser.parse_args()

# ============================================================
# 步骤 1：服务健康检查
# Step 1: Service Health Check
# ============================================================

print(f"\n🧪 Ragas 评估验证 | 后端: {args.backend}")

try:
    resp = httpx.get(f"{BASE_URL}/evaluation/info", timeout=HEALTH_CHECK_TIMEOUT)
    info = resp.json()
    active_backend = info["active_backend"]
    print(f"   服务状态: OK | 默认后端: {active_backend}")
except Exception as e:
    print(f"   ❗ 服务不可用: {e}")
    print("   请先启动: .venv\\Scripts\\python.exe -m uvicorn main:app --reload --port 8100")
    sys.exit(1)

# ============================================================
# 步骤 2：辅助函数
# Step 2: Helper Functions
# ============================================================


def print_scores(label, resp, elapsed):
    """打印单个测试用例的评分结果
    Print scores for a single test case"""
    if resp.status_code == 200:
        data = resp.json()
        scores = data["scores"]
        mode = data.get("details", {}).get("mode", "?")
        model = data.get("details", {}).get("model", "?")
        print(f"  {label}  ({elapsed}s)  [{mode} | {model}]")
        for metric, value in scores.items():
            # 生成可视化进度条
            # Generate visual progress bar
            filled = int(value * BAR_WIDTH)
            bar = "█" * filled + "░" * (BAR_WIDTH - filled)
            print(f"    {metric:25s} {bar} {value:.4f}")
    else:
        print(f"  {label}  ❗ HTTP {resp.status_code}")
        print(f"    {resp.text[:200]}")


def check_discrimination(label, scores):
    """检查评分是否具有区分度
    Check if scores discriminate good vs bad answers"""
    faith = scores.get("faithfulness", -1)
    if "忠实" in label:
        return faith > FAITHFULNESS_THRESHOLD
    return faith < FAITHFULNESS_THRESHOLD


def run_suite(endpoint, backend, title, metrics=None):
    """运行一组测试用例并返回是否全部通过
    Run a test suite and return pass/fail status"""
    print(f"\n{'═' * 60}")
    print(f"  {title}")
    print(f"{'═' * 60}")

    passed = 0
    total = len(CASES)

    with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
        for label, payload in CASES:
            # 构造请求体
            # Build request body
            req = {**payload, "backend": backend}
            if metrics:
                req["metrics"] = metrics

            # 发送请求并计时
            # Send request and measure elapsed time
            t0 = time.time()
            resp = client.post(f"{BASE_URL}{endpoint}", json=req)
            elapsed = round(time.time() - t0, 2)

            print_scores(label, resp, elapsed)

            # 区分度断言
            # Discrimination assertion
            if resp.status_code == 200:
                if check_discrimination(label, resp.json()["scores"]):
                    passed += 1

    status = "✅ PASS" if passed == total else f"⚠️  {passed}/{total}"
    print(f"\n  区分度检查: {status}")
    return passed == total


# ============================================================
# 步骤 3：快速评估验证
# Step 3: Quick Evaluation Verification
# ============================================================

ok_quick = run_suite(
    "/evaluation/quick",
    args.backend,
    f"⚡ 快速评估 (LLM-as-Judge) — {args.backend}",
)

# ============================================================
# 步骤 4：完整 Ragas 管道验证（可选）
# Step 4: Full Ragas Pipeline Verification (Optional)
# ============================================================

ok_full = True
if args.full:
    ok_full = run_suite(
        "/evaluation",
        args.backend,
        f"🔬 Ragas 完整管道 — {args.backend} (3 指标)",
        ALL_METRICS,
    )

# ============================================================
# 步骤 5：汇总结果
# Step 5: Summary
# ============================================================

all_passed = ok_quick and ok_full

print(f"\n{'═' * 60}")
print(f"  {'🎉 全部通过' if all_passed else '⚠️  有失败项'}")
print(f"{'═' * 60}\n")

sys.exit(0 if all_passed else 1)
