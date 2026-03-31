"""
DSPy Signatures Demo — 100% 使用 dspy 库 API

后端：Azure OpenAI (gpt-4o-mini) via litellm | Ollama (本地)
模式：
  /signatures       — 用 Signature 声明式生成回答（ChainOfThought）
  /signatures/verify — 3 组对比验证（事实题 / 推理题 / 无关上下文）

⚠️ DSPy v3 底层用 litellm，Azure 需要环境变量：
  AZURE_API_KEY, AZURE_API_BASE, AZURE_API_VERSION
  (不是 api_key= 参数)
"""

import os
import time

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel

load_dotenv()

router = APIRouter()

# ── 配置 ──────────────────────────────────────────────────────
AZURE_OAI_ENDPOINT = os.getenv("AZURE_OAI_ENDPOINT", "")
AZURE_OAI_KEY = os.getenv("AZURE_OAI_KEY", "")
AZURE_OAI_DEPLOYMENT = os.getenv("AZURE_OAI_DEPLOYMENT", "gpt-4o-mini")
AZURE_OAI_API_VERSION = os.getenv("AZURE_OAI_API_VERSION", "2024-12-01-preview")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")

USE_AZURE = bool(AZURE_OAI_KEY and AZURE_OAI_ENDPOINT)


# ── 请求 / 响应模型 ──────────────────────────────────────────

class SignatureRequest(BaseModel):
    question: str
    context: str = ""


class SignatureResponse(BaseModel):
    answer: str | None = None
    reasoning: str | None = None
    signature_info: dict
    elapsed_seconds: float | None = None
    error: str | None = None


# ═════════════════════════════════════════════════════════════
#  DSPy LM 初始化
#  ⚠️ DSPy v3 用 litellm 底层，Azure 需要设置环境变量
#  ⚠️ dspy.configure() 只能从同一个 async task 调用一次
#     后续请求必须用 dspy.context(lm=lm) 上下文管理器
# ═════════════════════════════════════════════════════════════

import dspy

# 设置 litellm Azure 环境变量（模块加载时执行一次）
if USE_AZURE:
    os.environ["AZURE_API_KEY"] = AZURE_OAI_KEY
    os.environ["AZURE_API_BASE"] = AZURE_OAI_ENDPOINT
    os.environ["AZURE_API_VERSION"] = AZURE_OAI_API_VERSION


def _get_lm():
    """创建 DSPy LM 实例（每次调用创建新实例避免状态冲突）"""
    if USE_AZURE:
        model_str = f"azure/{AZURE_OAI_DEPLOYMENT}"
        return dspy.LM(model_str, temperature=0, max_tokens=500, cache=False), model_str
    else:
        model_str = f"ollama_chat/{OLLAMA_MODEL}"
        return dspy.LM(model_str, api_base=OLLAMA_BASE_URL, temperature=0, cache=False), model_str


# ═════════════════════════════════════════════════════════════
#  核心演示 — Signature 声明式生成
# ═════════════════════════════════════════════════════════════

# ── Signature 定义（模块级，只定义一次）──
class RAGAnswer(dspy.Signature):
    """回答基于检索到的上下文的问题，必须忠于上下文内容"""
    context: str = dspy.InputField(desc="检索到的相关文档")
    question: str = dspy.InputField(desc="用户问题")
    answer: str = dspy.OutputField(desc="基于上下文的准确回答")


class RAGAnswerStrict(dspy.Signature):
    """回答基于检索到的上下文的问题，必须忠于上下文内容。如果上下文中没有相关信息，请说明无法回答。"""
    context: str = dspy.InputField(desc="检索到的相关文档")
    question: str = dspy.InputField(desc="用户问题")
    answer: str = dspy.OutputField(desc="基于上下文的准确回答")


@router.post("/signatures", response_model=SignatureResponse)
async def run_signature(req: SignatureRequest):
    """用 DSPy Signature 声明式生成回答"""
    start = time.time()

    try:
        lm, model_str = _get_lm()

        signature_info = {
            "source": "dspy.Signature + dspy.ChainOfThought",
            "input_fields": ["context", "question"],
            "output_fields": ["answer", "reasoning"],
            "instruction": RAGAnswer.__doc__,
            "backend": model_str,
        }

        # ⚠️ 用 dspy.context() 替代 dspy.configure()，避免 async task 冲突
        predict = dspy.ChainOfThought(RAGAnswer)
        with dspy.context(lm=lm):
            result = predict(context=req.context[:1000], question=req.question)

        answer = result.answer
        reasoning = getattr(result, "reasoning", None)
        elapsed = round(time.time() - start, 2)

        logger.success("DSPy Signature 完成 | {elapsed}s | answer_len={alen}",
                        elapsed=elapsed, alen=len(answer or ""))

        return SignatureResponse(
            answer=answer,
            reasoning=reasoning,
            signature_info=signature_info,
            elapsed_seconds=elapsed,
        )

    except ImportError as e:
        return SignatureResponse(
            signature_info={},
            error=f"依赖缺失: {e}. 运行: uv add dspy",
        )
    except Exception as e:
        logger.exception("DSPy Signature 失败")
        raise HTTPException(status_code=500, detail=str(e))


# ═════════════════════════════════════════════════════════════
#  对比验证 — 3 组用例一键对比
#  核心价值：Signature 的声明式约束让 LLM 更忠于上下文
# ═════════════════════════════════════════════════════════════

VERIFY_CASES = [
    {
        "label": "✅ 简单事实题",
        "type": "factual",
        "question": "什么是光合作用？",
        "context": (
            "光合作用（Photosynthesis）是植物、藻类和某些细菌利用光能"
            "将二氧化碳和水转化为葡萄糖和氧气的生化过程。"
            "主要发生在叶绿体中。"
        ),
    },
    {
        "label": "🧠 推理题",
        "type": "reasoning",
        "question": "如果植物被关在黑暗的屋子里，光合作用会怎样？",
        "context": (
            "光合作用需要光能作为能量来源。在无光条件下，"
            "光反应无法进行，导致 ATP 和 NADPH 无法生成，"
            "暗反应也因此停止。植物会转而进行细胞呼吸消耗储存的有机物。"
        ),
    },
    {
        "label": "🚫 无关上下文",
        "type": "irrelevant_context",
        "question": "牛顿第三定律是什么？",
        "context": (
            "光合作用（Photosynthesis）是植物、藻类和某些细菌利用光能"
            "将二氧化碳和水转化为葡萄糖和氧气的生化过程。"
        ),
    },
]


class VerifyCaseResult(BaseModel):
    label: str
    case_type: str
    question: str
    context: str
    answer: str | None
    reasoning: str | None
    elapsed_seconds: float
    passed: bool
    pass_reason: str


class VerifyResponse(BaseModel):
    cases: list[VerifyCaseResult]
    all_passed: bool
    total_elapsed: float
    backend: str


@router.post("/signatures/verify", response_model=VerifyResponse)
async def run_verification():
    """一键对比验证 — 3 组用例测试 Signature 声明式约束效果"""
    total_start = time.time()
    results: list[VerifyCaseResult] = []

    try:
        lm, model_str = _get_lm()
        predict = dspy.ChainOfThought(RAGAnswerStrict)
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"依赖缺失: {e}")

    logger.info("DSPy 对比验证开始 | backend={} | {} 组用例", model_str, len(VERIFY_CASES))

    for case in VERIFY_CASES:
        t0 = time.time()
        answer = None
        reasoning = None
        passed = False
        pass_reason = ""

        try:
            # ⚠️ 用 dspy.context() 避免 async task 冲突
            with dspy.context(lm=lm):
                result = predict(
                    context=case["context"],
                    question=case["question"],
                )
            answer = result.answer
            reasoning = getattr(result, "reasoning", None)

            # ── 区分度检查 ──
            if case["type"] == "factual":
                has_relevant = any(kw in (answer or "") for kw in ["光", "植物", "光能", "二氧化碳", "葡萄糖"])
                passed = has_relevant and len(answer or "") > 10
                pass_reason = "回答包含上下文关键信息" if passed else "回答未提及上下文关键词"

            elif case["type"] == "reasoning":
                has_reasoning = any(kw in (answer or "") for kw in ["停止", "无法", "不能", "呼吸", "光反应", "暗反应", "没有光"])
                passed = has_reasoning and len(answer or "") > 15
                pass_reason = "回答包含推理过程" if passed else "回答未展示基于上下文的推理"

            elif case["type"] == "irrelevant_context":
                refuses = any(kw in (answer or "").lower() for kw in [
                    "无法", "没有", "不包含", "未提供", "无关", "不能",
                    "无", "cannot", "context", "上下文", "不涉及",
                ])
                makes_up = any(kw in (answer or "") for kw in ["作用力", "反作用力", "牛顿"])
                if refuses:
                    passed = True
                    pass_reason = "正确拒绝 — 识别到上下文无关信息"
                elif makes_up:
                    passed = False
                    pass_reason = "瞎编 — 上下文是光合作用，却回答了物理知识"
                else:
                    passed = False
                    pass_reason = "未明确拒绝，不符合预期"

        except Exception as e:
            answer = None
            passed = False
            pass_reason = f"调用失败: {e}"
            logger.error("验证用例 {} 失败: {}", case["label"], e)

        elapsed = round(time.time() - t0, 2)

        results.append(VerifyCaseResult(
            label=case["label"],
            case_type=case["type"],
            question=case["question"],
            context=case["context"][:100] + "...",
            answer=answer,
            reasoning=reasoning,
            elapsed_seconds=elapsed,
            passed=passed,
            pass_reason=pass_reason,
        ))
        logger.debug("  {} | passed={} | {:.2f}s | {}",
                      case["label"], passed, elapsed, pass_reason)

    all_passed = all(r.passed for r in results)
    total_elapsed = round(time.time() - total_start, 2)

    status = "✅ 全部通过" if all_passed else "⚠️ 有失败项"
    logger.success("DSPy 对比验证完成 | {} | {:.2f}s", status, total_elapsed)

    return VerifyResponse(
        cases=results,
        all_passed=all_passed,
        total_elapsed=total_elapsed,
        backend=model_str,
    )


# ═════════════════════════════════════════════════════════════
#  Info
# ═════════════════════════════════════════════════════════════

@router.get("/signatures/info")
async def signatures_info():
    model_str = f"azure/{AZURE_OAI_DEPLOYMENT}" if USE_AZURE else f"ollama/{OLLAMA_MODEL}"
    return {
        "module": "dspy-signatures",
        "source_library": "dspy",
        "active_backend": model_str,
        "features": [
            "声明式 Signature 定义输入/输出",
            "ChainOfThought 思维链推理",
            "BootstrapFewShot 自动优化 prompt",
        ],
        "modes": {
            "signatures": "/signatures — 声明式生成回答",
            "verify": "/signatures/verify — 3 组对比验证",
        },
    }
