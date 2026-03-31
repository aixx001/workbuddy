"""
Module Market — DSPy Signatures Module Verification
Verify Signature declarative generation and context-grounding behavior.

Usage:
  .venv\\Scripts\\python.exe workflows\\verify_dspy_signatures.py
  .venv\\Scripts\\python.exe workflows\\verify_dspy_signatures.py --backend ollama

验证项：
  1. 简单事实题 — 应回答忠于上下文
  2. 推理题     — 应基于上下文推理
  3. 无关题     — 应拒绝回答（上下文无关）
"""

import argparse
import json
import pathlib
import sys
import time

import httpx

# ============================================================
# 配置常量
# Configuration Constants
# ============================================================

BASE_URL = "http://localhost:8100/demo/dspy"
REQUEST_TIMEOUT = 120
HEALTH_CHECK_TIMEOUT = 5
RESULTS_DIR = pathlib.Path(__file__).parent.parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = RESULTS_DIR / "verify_dspy-signatures.json"

# ============================================================
# 测试用例定义
# Test Case Definitions
# ============================================================

# 三组对比用例：事实题 / 推理题 / 无关上下文
# Three contrastive cases: factual / reasoning / irrelevant context
CASES = [
    ("✅ 简单事实题", "factual", {
        "question": "什么是光合作用？",
        "context": (
            "光合作用（Photosynthesis）是植物、藻类和某些细菌利用光能"
            "将二氧化碳和水转化为葡萄糖和氧气的生化过程。"
            "主要发生在叶绿体中。"
        ),
    }),
    ("🧠 推理题", "reasoning", {
        "question": "如果植物被关在黑暗的屋子里，光合作用会怎样？",
        "context": (
            "光合作用需要光能作为能量来源。在无光条件下，"
            "光反应无法进行，导致 ATP 和 NADPH 无法生成，"
            "暗反应也因此停止。植物会转而进行细胞呼吸消耗储存的有机物。"
        ),
    }),
    ("🚫 无关上下文", "irrelevant_context", {
        "question": "牛顿第三定律是什么？",
        "context": (
            "光合作用（Photosynthesis）是植物、藻类和某些细菌利用光能"
            "将二氧化碳和水转化为葡萄糖和氧气的生化过程。"
        ),
    }),
]

# ============================================================
# 解析命令行参数
# Parse CLI Arguments
# ============================================================

parser = argparse.ArgumentParser(description="DSPy Signatures 模块验证")
parser.add_argument("--backend", default="azure", choices=["azure", "ollama"],
                    help="评估后端 (默认: azure)")
args = parser.parse_args()

# ============================================================
# 步骤 1：服务健康检查
# Step 1: Service Health Check
# ============================================================

print(f"\n🧪 DSPy Signatures 验证 | 后端: {args.backend}")
print("─" * 60)

try:
    resp = httpx.get(f"{BASE_URL}/signatures/info", timeout=HEALTH_CHECK_TIMEOUT)
    info = resp.json()
    active_backend = info.get("active_backend", "unknown")
    print(f"   服务状态: OK | 当前后端: {active_backend}")
except Exception as e:
    print(f"   ❗ 服务不可用: {e}")
    print("   请先启动: .venv\\Scripts\\python.exe -m uvicorn main:app --reload --port 8100")
    sys.exit(1)

# ============================================================
# 步骤 2：逐个运行测试用例
# Step 2: Run Each Test Case
# ============================================================

print(f"\n{'═' * 60}")
print(f"  🔬 DSPy Signature 声明式生成 — 3 组对比验证")
print(f"{'═' * 60}")

results = []
total_start = time.time()

with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
    for label, case_type, payload in CASES:
        print(f"\n  {label}")
        print(f"  问题: {payload['question']}")
        print(f"  上下文: {payload['context'][:60]}...")

        # 发送请求并计时
        # Send request and measure elapsed time
        t0 = time.time()
        try:
            resp = client.post(f"{BASE_URL}/signatures", json=payload)
            elapsed = round(time.time() - t0, 2)

            if resp.status_code != 200:
                print(f"  ❗ HTTP {resp.status_code}: {resp.text[:200]}")
                results.append({
                    "label": label, "case_type": case_type,
                    "passed": False, "error": f"HTTP {resp.status_code}",
                    "elapsed_seconds": elapsed,
                })
                continue

            data = resp.json()

            if data.get("error"):
                print(f"  ❗ 错误: {data['error']}")
                results.append({
                    "label": label, "case_type": case_type,
                    "passed": False, "error": data["error"],
                    "elapsed_seconds": elapsed,
                })
                continue

            answer = data.get("answer", "")
            reasoning = data.get("reasoning", "")
            backend_used = data.get("signature_info", {}).get("backend", "?")

            print(f"  回答: {answer[:120]}")
            if reasoning:
                print(f"  推理: {reasoning[:120]}")
            print(f"  耗时: {elapsed}s | 后端: {backend_used}")

            # ── 区分度检查 ──
            # Discrimination check
            passed = False
            pass_reason = ""

            if case_type == "factual":
                # 简单事实题：应该给出正确答案
                has_relevant = any(kw in answer for kw in ["光", "植物", "光能", "二氧化碳", "葡萄糖"])
                passed = has_relevant and len(answer) > 10
                pass_reason = "回答包含上下文关键信息" if passed else "回答未提及上下文关键词"

            elif case_type == "reasoning":
                # 推理题：应该基于上下文推理
                has_reasoning = any(kw in answer for kw in ["停止", "无法", "不能", "呼吸", "光反应", "暗反应", "没有光"])
                passed = has_reasoning and len(answer) > 15
                pass_reason = "回答包含推理过程" if passed else "回答未展示基于上下文的推理"

            elif case_type == "irrelevant_context":
                # 无关上下文：应该拒绝回答或表示无法从上下文找到答案
                refuses = any(kw in answer.lower() for kw in [
                    "无法", "没有", "不包含", "未提供", "无关", "不能",
                    "无", "cannot", "context", "上下文", "不涉及",
                ])
                makes_up = any(kw in answer for kw in ["作用力", "反作用力", "牛顿"])
                if refuses:
                    passed = True
                    pass_reason = "正确拒绝 — 识别到上下文无关信息"
                elif makes_up:
                    passed = False
                    pass_reason = "瞎编 — 上下文是光合作用，却回答了物理知识"
                else:
                    # 如果回答既没拒绝也没瞎编，属于模糊地带
                    passed = False
                    pass_reason = "未明确拒绝，也没瞎编，但不符合预期"

            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  区分度: {status} — {pass_reason}")

            results.append({
                "label": label,
                "case_type": case_type,
                "question": payload["question"],
                "context": payload["context"][:100] + "...",
                "answer": answer,
                "reasoning": reasoning,
                "elapsed_seconds": elapsed,
                "passed": passed,
                "pass_reason": pass_reason,
                "backend": backend_used,
            })

        except Exception as e:
            elapsed = round(time.time() - t0, 2)
            print(f"  ❗ 异常: {e}")
            results.append({
                "label": label, "case_type": case_type,
                "passed": False, "error": str(e),
                "elapsed_seconds": elapsed,
            })

total_elapsed = round(time.time() - total_start, 2)

# ============================================================
# 步骤 3：汇总结果
# Step 3: Summary
# ============================================================

passed_count = sum(1 for r in results if r["passed"])
total_count = len(results)
all_passed = passed_count == total_count

print(f"\n{'═' * 60}")
print(f"  区分度检查: {'✅ PASS' if all_passed else f'⚠️  {passed_count}/{total_count}'}")
print(f"  总耗时: {total_elapsed}s")
print(f"{'═' * 60}")

# ============================================================
# 步骤 4：保存完整结果
# Step 4: Save Full Results
# ============================================================

output_data = {
    "module": "dspy-signatures",
    "backend": args.backend,
    "cases": results,
    "all_passed": all_passed,
    "total_elapsed": total_elapsed,
    "verified_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
}

OUTPUT_FILE.write_text(
    json.dumps(output_data, indent=2, ensure_ascii=False),
    encoding="utf-8",
)
print(f"\n  💾 结果已保存: {OUTPUT_FILE}")

if all_passed:
    print("  🎉 全部通过！可以更新前端了。\n")
else:
    print("  ⚠️ 有失败项，需要检查后端或调整验证标准。\n")

sys.exit(0 if all_passed else 1)
