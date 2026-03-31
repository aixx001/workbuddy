"""
DeepEval Demo — 100% 使用 deepeval 库 API

后端：Azure OpenAI (gpt-4o-mini) | 或 OPENAI_API_KEY
模式：
  /evaluation       — FaithfulnessMetric + GEval 评估
  /evaluation/verify — 3 组对比验证（区分度检查）
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

USE_AZURE = bool(AZURE_OAI_KEY and AZURE_OAI_ENDPOINT)


# ── Azure LLM 适配 ───────────────────────────────────────────

_cached_model = None


def _get_deepeval_model():
    """获取 DeepEval 用的 LLM 模型（Azure 优先）"""
    global _cached_model
    if _cached_model is not None:
        return _cached_model

    if USE_AZURE:
        from deepeval.models.base_model import DeepEvalBaseLLM
        from langchain_openai import AzureChatOpenAI

        class AzureOpenAIWrapper(DeepEvalBaseLLM):
            def __init__(self, model):
                self.model = model

            def load_model(self):
                return self.model

            def generate(self, prompt: str) -> str:
                return self.model.invoke(prompt).content

            async def a_generate(self, prompt: str) -> str:
                res = await self.model.ainvoke(prompt)
                return res.content

            def get_model_name(self) -> str:
                return f"azure/{AZURE_OAI_DEPLOYMENT}"

        llm = AzureChatOpenAI(
            azure_endpoint=AZURE_OAI_ENDPOINT,
            api_key=AZURE_OAI_KEY,
            azure_deployment=AZURE_OAI_DEPLOYMENT,
            api_version=AZURE_OAI_API_VERSION,
            temperature=0,
        )
        _cached_model = AzureOpenAIWrapper(model=llm)
        logger.info("DeepEval 使用 Azure OpenAI | deployment={}", AZURE_OAI_DEPLOYMENT)
    else:
        _cached_model = None  # DeepEval 会 fallback 到 OPENAI_API_KEY
        logger.info("DeepEval 使用默认 OpenAI (OPENAI_API_KEY)")

    return _cached_model


# ── 请求 / 响应模型 ──────────────────────────────────────────

class DeepEvalRequest(BaseModel):
    question: str
    answer: str
    contexts: list[str] = []
    custom_criteria: str | None = None


class DeepEvalResponse(BaseModel):
    scores: dict[str, float | None]
    details: dict
    error: str | None = None


# ═════════════════════════════════════════════════════════════
#  评估 — 全量指标
#  Faithfulness + Hallucination + AnswerRelevancy + GEval
# ═════════════════════════════════════════════════════════════

@router.post("/evaluation", response_model=DeepEvalResponse)
async def run_deepeval(req: DeepEvalRequest):
    """用 deepeval 全量指标评估 LLM 输出质量"""
    start = time.time()
    model = _get_deepeval_model()
    backend_label = f"azure/{AZURE_OAI_DEPLOYMENT}" if USE_AZURE else "openai"
    logger.info("DeepEval 评估开始 | backend={} contexts={} custom_criteria={}",
                backend_label, len(req.contexts), bool(req.custom_criteria))

    try:
        from deepeval.test_case import LLMTestCase

        test_case = LLMTestCase(
            input=req.question,
            actual_output=req.answer,
            retrieval_context=req.contexts if req.contexts else None,
            context=req.contexts if req.contexts else None,  # HallucinationMetric 需要
        )

        scores: dict[str, float | None] = {}
        details: dict = {"metrics_used": [], "backend": backend_label}

        # ① Faithfulness — 回答是否忠于上下文（有没有依据）
        if req.contexts:
            try:
                from deepeval.metrics import FaithfulnessMetric
                metric = FaithfulnessMetric(threshold=0.7, model=model)
                metric.measure(test_case)
                scores["faithfulness"] = round(metric.score, 4) if metric.score is not None else None
                details["metrics_used"].append("FaithfulnessMetric")
                details["faithfulness_reason"] = metric.reason
            except Exception as e:
                scores["faithfulness"] = None
                details["faithfulness_error"] = str(e)

        # ② Hallucination — 回答是否矛盾了上下文（有没有瞎编）
        if req.contexts:
            try:
                from deepeval.metrics import HallucinationMetric
                metric = HallucinationMetric(threshold=0.5, model=model)
                metric.measure(test_case)
                scores["hallucination"] = round(metric.score, 4) if metric.score is not None else None
                details["metrics_used"].append("HallucinationMetric")
                details["hallucination_reason"] = metric.reason
            except Exception as e:
                scores["hallucination"] = None
                details["hallucination_error"] = str(e)

        # ③ Answer Relevancy — 回答是否切题
        if req.contexts:
            try:
                from deepeval.metrics import AnswerRelevancyMetric
                metric = AnswerRelevancyMetric(threshold=0.7, model=model)
                metric.measure(test_case)
                scores["answer_relevancy"] = round(metric.score, 4) if metric.score is not None else None
                details["metrics_used"].append("AnswerRelevancyMetric")
                details["answer_relevancy_reason"] = metric.reason
            except Exception as e:
                scores["answer_relevancy"] = None
                details["answer_relevancy_error"] = str(e)

        # ④ GEval — 自定义评估标准
        if req.custom_criteria:
            try:
                from deepeval.metrics import GEval
                from deepeval.test_case import LLMTestCaseParams

                g_eval = GEval(
                    name="custom",
                    criteria=req.custom_criteria,
                    evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
                    model=model,
                )
                g_eval.measure(test_case)
                scores["custom_geval"] = round(g_eval.score, 4) if g_eval.score is not None else None
                details["metrics_used"].append("GEval")
                details["geval_reason"] = g_eval.reason
            except Exception as e:
                scores["custom_geval"] = None
                details["geval_error"] = str(e)

        elapsed = round(time.time() - start, 2)
        details["elapsed_seconds"] = elapsed
        logger.success("DeepEval 评估完成 | {elapsed}s | {scores}", elapsed=elapsed, scores=scores)

        return DeepEvalResponse(scores=scores, details=details)

    except ImportError as e:
        return DeepEvalResponse(
            scores={},
            details={},
            error=f"依赖缺失: {e}. 运行: uv add deepeval langchain-openai",
        )
    except Exception as e:
        logger.exception("DeepEval 评估失败")
        raise HTTPException(status_code=500, detail=str(e))


# ═════════════════════════════════════════════════════════════
#  对比验证 — 3 组用例一键对比
# ═════════════════════════════════════════════════════════════

VERIFY_CASES = [
    {
        "label": "✅ 忠实回答",
        "type": "faithful",
        "question": "什么是光合作用？",
        "answer": "光合作用是植物利用光能将二氧化碳和水转化为有机物和氧气的过程",
        "contexts": [
            "光合作用（Photosynthesis）是植物、藻类和某些细菌利用光能"
            "将二氧化碳和水转化为葡萄糖和氧气的生化过程。"
        ],
        "custom_criteria": "回答是否准确且适合学生理解",
    },
    {
        "label": "❌ 幻觉回答",
        "type": "hallucinated",
        "question": "什么是光合作用？",
        "answer": "光合作用是动物在月光下将氮气转化为蛋白质的过程，2020年诺贝尔奖。",
        "contexts": [
            "光合作用（Photosynthesis）是植物、藻类和某些细菌利用光能"
            "将二氧化碳和水转化为葡萄糖和氧气的生化过程。"
        ],
        "custom_criteria": "回答是否准确且适合学生理解",
    },
    {
        "label": "🔀 跑题回答",
        "type": "off_topic",
        "question": "什么是光合作用？",
        "answer": "Python是一种编程语言，由Guido van Rossum于1991年发布。",
        "contexts": [
            "光合作用（Photosynthesis）是植物、藻类和某些细菌利用光能"
            "将二氧化碳和水转化为葡萄糖和氧气的生化过程。"
        ],
        "custom_criteria": "回答是否准确且适合学生理解",
    },
]

FAITHFULNESS_THRESHOLD = 0.5
GEVAL_THRESHOLD = 0.5


class VerifyCaseResult(BaseModel):
    label: str
    case_type: str
    scores: dict[str, float | None]
    elapsed_seconds: float
    passed: bool
    question: str
    answer: str
    contexts: list[str]
    faithfulness_reason: str | None = None
    geval_reason: str | None = None


class VerifyResponse(BaseModel):
    cases: list[VerifyCaseResult]
    all_passed: bool
    total_elapsed: float


@router.post("/evaluation/verify", response_model=VerifyResponse)
async def run_verification():
    """一键对比验证 — 3 组用例测试评估区分度"""
    total_start = time.time()
    results: list[VerifyCaseResult] = []

    model = _get_deepeval_model()
    backend_label = f"azure/{AZURE_OAI_DEPLOYMENT}" if USE_AZURE else "openai"
    logger.info("DeepEval 对比验证开始 | backend={} | {} 组用例", backend_label, len(VERIFY_CASES))

    for case in VERIFY_CASES:
        t0 = time.time()
        scores: dict[str, float | None] = {}
        reasons: dict[str, str | None] = {}

        try:
            from deepeval.test_case import LLMTestCase
            from deepeval.test_case import LLMTestCaseParams

            test_case = LLMTestCase(
                input=case["question"],
                actual_output=case["answer"],
                retrieval_context=case["contexts"],
                context=case["contexts"],  # HallucinationMetric 需要 context (ground truth)
            )

            # ① Faithfulness
            try:
                from deepeval.metrics import FaithfulnessMetric
                metric = FaithfulnessMetric(threshold=0.7, model=model)
                metric.measure(test_case)
                scores["faithfulness"] = round(metric.score, 4) if metric.score is not None else None
                reasons["faithfulness"] = metric.reason
            except Exception as e:
                scores["faithfulness"] = None
                logger.warning("Faithfulness 评估失败: {}", e)

            # ② Hallucination
            try:
                from deepeval.metrics import HallucinationMetric
                metric = HallucinationMetric(threshold=0.5, model=model)
                metric.measure(test_case)
                scores["hallucination"] = round(metric.score, 4) if metric.score is not None else None
                reasons["hallucination"] = metric.reason
            except Exception as e:
                scores["hallucination"] = None
                logger.warning("Hallucination 评估失败: {}", e)

            # ③ Answer Relevancy
            try:
                from deepeval.metrics import AnswerRelevancyMetric
                metric = AnswerRelevancyMetric(threshold=0.7, model=model)
                metric.measure(test_case)
                scores["answer_relevancy"] = round(metric.score, 4) if metric.score is not None else None
                reasons["answer_relevancy"] = metric.reason
            except Exception as e:
                scores["answer_relevancy"] = None
                logger.warning("AnswerRelevancy 评估失败: {}", e)

            # ④ GEval
            try:
                from deepeval.metrics import GEval
                g_eval = GEval(
                    name="custom",
                    criteria=case["custom_criteria"],
                    evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
                    model=model,
                )
                g_eval.measure(test_case)
                scores["custom_geval"] = round(g_eval.score, 4) if g_eval.score is not None else None
                reasons["custom_geval"] = g_eval.reason
            except Exception as e:
                scores["custom_geval"] = None
                logger.warning("GEval 评估失败: {}", e)

        except ImportError as e:
            logger.error("依赖缺失: {}", e)
            scores = {k: None for k in ["faithfulness", "hallucination", "answer_relevancy", "custom_geval"]}
        except Exception as e:
            logger.error("验证用例 {} 失败: {}", case["label"], e)
            scores = {k: None for k in ["faithfulness", "hallucination", "answer_relevancy", "custom_geval"]}

        elapsed = round(time.time() - t0, 2)

        # 区分度检查 — 任意一个指标判对即 pass
        valid_scores = {k: v for k, v in scores.items() if v is not None}
        if case["type"] == "faithful":
            # 忠实回答应该得高分
            passed = any(v > 0.5 for v in valid_scores.values()) if valid_scores else False
        else:
            # 幻觉/跑题回答应该至少有一个指标给低分
            passed = any(v < 0.5 for v in valid_scores.values()) if valid_scores else False

        results.append(VerifyCaseResult(
            label=case["label"],
            case_type=case["type"],
            scores=scores,
            elapsed_seconds=elapsed,
            passed=passed,
            question=case["question"],
            answer=case["answer"],
            contexts=case["contexts"],
            faithfulness_reason=reasons.get("faithfulness"),
            geval_reason=reasons.get("custom_geval"),
        ))
        score_str = " | ".join(f"{k}={v}" for k, v in scores.items())
        logger.debug("  {} | {} | passed={} | {:.2f}s",
                      case["label"], score_str, passed, elapsed)

    all_passed = all(r.passed for r in results)
    total_elapsed = round(time.time() - total_start, 2)

    status = "✅ 全部通过" if all_passed else "⚠️ 有失败项"
    logger.success("DeepEval 对比验证完成 | {} | {:.2f}s", status, total_elapsed)

    return VerifyResponse(
        cases=results,
        all_passed=all_passed,
        total_elapsed=total_elapsed,
    )


# ═════════════════════════════════════════════════════════════
#  Info
# ═════════════════════════════════════════════════════════════

@router.get("/evaluation/info")
async def deepeval_info():
    return {
        "module": "deepeval",
        "source_library": "deepeval",
        "active_backend": f"azure/{AZURE_OAI_DEPLOYMENT}" if USE_AZURE else "openai",
        "backends": {
            "azure": {"available": USE_AZURE, "model": AZURE_OAI_DEPLOYMENT},
            "openai": {"available": bool(os.getenv("OPENAI_API_KEY"))},
        },
        "available_metrics": [
            "FaithfulnessMetric",
            "AnswerRelevancyMetric",
            "GEval (自定义标准)",
            "HallucinationMetric",
        ],
        "modes": {
            "evaluation": "/evaluation — FaithfulnessMetric + GEval",
            "verify": "/evaluation/verify — 3 组对比验证",
        },
    }
