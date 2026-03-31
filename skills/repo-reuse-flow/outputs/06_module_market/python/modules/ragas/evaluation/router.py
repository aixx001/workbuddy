"""
Evaluation Demo — RAG 质量评估

后端：azure (gpt-4o-mini) | ollama (本地)
模式：
  /evaluation/quick  — 单次 LLM-as-Judge（2-10s）
  /evaluation         — 完整 Ragas 管道（15-60s）
"""

import json
import os
import re
import time

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel

load_dotenv()

router = APIRouter()

# ── 配置 ──────────────────────────────────────────────────────
EVAL_BACKEND = os.getenv("EVAL_BACKEND", "ollama")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

AZURE_OAI_ENDPOINT = os.getenv("AZURE_OAI_ENDPOINT", "")
AZURE_OAI_KEY = os.getenv("AZURE_OAI_KEY", "")
AZURE_OAI_DEPLOYMENT = os.getenv("AZURE_OAI_DEPLOYMENT", "gpt-4o-mini")
AZURE_OAI_API_VERSION = os.getenv("AZURE_OAI_API_VERSION", "2024-12-01-preview")


# ── 请求 / 响应模型 ──────────────────────────────────────────
class EvalRequest(BaseModel):
    question: str
    answer: str
    contexts: list[str]
    reference: str | None = None
    metrics: list[str] | None = None
    model: str | None = None
    backend: str | None = None  # azure / ollama


class EvalResponse(BaseModel):
    scores: dict[str, float]
    details: dict | None = None
    error: str | None = None


# ═════════════════════════════════════════════════════════════
#  快速评估 — 单次 LLM-as-Judge
# ═════════════════════════════════════════════════════════════

JUDGE_PROMPT = """\
你是一个 RAG 系统质量评估专家。请根据以下信息，对回答质量打分。

**问题**: {question}
**检索到的上下文**: {contexts}
**系统回答**: {answer}
**参考答案**: {reference}

请对以下三个维度分别打分（0.0 到 1.0），用严格 JSON 返回：
1. faithfulness — 回答是否忠于上下文？（有无幻觉）
2. answer_relevancy — 回答是否切题？
3. context_precision — 上下文是否与问题相关？

只返回 JSON：
{{"faithfulness": 0.0, "answer_relevancy": 0.0, "context_precision": 0.0}}
"""


@router.post("/evaluation/quick", response_model=EvalResponse)
async def run_quick_evaluation(req: EvalRequest):
    """单次 LLM 调用快速评估"""
    backend = req.backend or EVAL_BACKEND
    start = time.time()

    logger.info("快速评估开始 | backend={} model={}", backend,
                req.model or (AZURE_OAI_DEPLOYMENT if backend == "azure" else OLLAMA_MODEL))

    try:
        prompt = JUDGE_PROMPT.format(
            question=req.question,
            answer=req.answer,
            contexts="\n---\n".join(req.contexts),
            reference=req.reference or "（无参考答案）",
        )

        raw, model_used = (
            await _call_azure(prompt) if backend == "azure"
            else await _call_ollama(prompt, req.model)
        )

        scores = _parse_judge_scores(raw)
        elapsed = round(time.time() - start, 2)

        logger.success("快速评估完成 | {elapsed}s | {scores}", elapsed=elapsed, scores=scores)

        return EvalResponse(
            scores=scores,
            details={
                "mode": "quick (LLM-as-Judge)",
                "backend": backend,
                "model": model_used,
                "elapsed_seconds": elapsed,
            },
        )
    except Exception as e:
        logger.exception("快速评估失败 | backend={}", backend)
        raise HTTPException(status_code=500, detail=str(e))


# ── LLM 调用 ─────────────────────────────────────────────────

async def _call_azure(prompt: str) -> tuple[str, str]:
    import httpx

    url = (
        f"{AZURE_OAI_ENDPOINT.rstrip('/')}/openai/deployments/"
        f"{AZURE_OAI_DEPLOYMENT}/chat/completions?api-version={AZURE_OAI_API_VERSION}"
    )

    logger.debug("Azure 请求 → {}", AZURE_OAI_DEPLOYMENT)
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, headers={
            "api-key": AZURE_OAI_KEY,
            "Content-Type": "application/json",
        }, json={
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": 200,
        })
        resp.raise_for_status()
        data = resp.json()

    content = data["choices"][0]["message"]["content"]
    model = data.get("model", AZURE_OAI_DEPLOYMENT)
    logger.debug("Azure 响应 ← {} chars | model={}", len(content), model)
    return content, model


async def _call_ollama(prompt: str, model_override: str | None = None) -> tuple[str, str]:
    import httpx

    model = model_override or OLLAMA_MODEL
    logger.debug("Ollama 请求 → {}", model)

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "think": False,
            "options": {"temperature": 0, "num_ctx": 2048},
        })
        resp.raise_for_status()
        data = resp.json()

    content = data["message"]["content"]
    logger.debug("Ollama 响应 ← {} chars", len(content))
    return content, model


# ── 分数解析 ──────────────────────────────────────────────────

VALID_METRICS = {"faithfulness", "answer_relevancy", "context_precision"}


def _parse_judge_scores(raw: str) -> dict[str, float]:
    """从 LLM 输出提取 JSON 分数，带容错"""
    # 尝试 JSON 解析
    try:
        cleaned = re.sub(r"```json?\s*|\s*```", "", raw).strip()
        obj = json.loads(cleaned)
        return {k: round(float(v), 4) for k, v in obj.items() if k in VALID_METRICS}
    except (json.JSONDecodeError, ValueError):
        pass

    # fallback: 正则
    scores = {}
    for m in VALID_METRICS:
        match = re.search(rf'"{m}"\s*:\s*([\d.]+)', raw)
        if match:
            scores[m] = round(float(match.group(1)), 4)

    if scores:
        return scores

    raise ValueError(f"无法解析分数: {raw[:200]}")


# ═════════════════════════════════════════════════════════════
#  完整 Ragas 评估
# ═════════════════════════════════════════════════════════════

def _get_ragas_llm(backend: str, model_name: str | None = None):
    from ragas.llms import LangchainLLMWrapper

    if backend == "azure":
        from langchain_openai import AzureChatOpenAI
        llm = AzureChatOpenAI(
            azure_endpoint=AZURE_OAI_ENDPOINT,
            api_key=AZURE_OAI_KEY,
            azure_deployment=model_name or AZURE_OAI_DEPLOYMENT,
            api_version=AZURE_OAI_API_VERSION,
            temperature=0,
        )
    else:
        from langchain_ollama import ChatOllama
        llm = ChatOllama(
            model=model_name or OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0,
            num_ctx=4096,
            extra_body={"think": False},
        )
    return LangchainLLMWrapper(llm)


def _get_ragas_embeddings():
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from langchain_ollama import OllamaEmbeddings
    return LangchainEmbeddingsWrapper(
        OllamaEmbeddings(model=OLLAMA_EMBED_MODEL, base_url=OLLAMA_BASE_URL)
    )


@router.post("/evaluation", response_model=EvalResponse)
async def run_evaluation(req: EvalRequest):
    """完整 Ragas 管道评估"""
    backend = req.backend or EVAL_BACKEND
    start = time.time()

    try:
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy, context_precision
        from ragas.dataset_schema import SingleTurnSample, EvaluationDataset
        from ragas.run_config import RunConfig

        sample = SingleTurnSample(
            user_input=req.question,
            response=req.answer,
            retrieved_contexts=req.contexts,
            reference=req.reference,
        )

        metric_map = {
            "faithfulness": faithfulness,
            "answer_relevancy": answer_relevancy,
            "context_precision": context_precision,
        }
        selected = (
            [metric_map[m] for m in req.metrics if m in metric_map]
            if req.metrics
            else [metric_map["faithfulness"]]
        )

        metric_names = [m.name for m in selected]
        logger.info("Ragas 评估开始 | backend={} metrics={}", backend, metric_names)

        llm = _get_ragas_llm(backend, req.model)
        embeddings = _get_ragas_embeddings()
        timeout = 60 if backend == "azure" else 600
        run_config = RunConfig(max_workers=1, max_wait=timeout, timeout=timeout)

        dataset = EvaluationDataset(samples=[sample])
        result = evaluate(
            dataset=dataset,
            metrics=selected,
            llm=llm,
            embeddings=embeddings,
            run_config=run_config,
        )

        # result.to_pandas() 返回 DataFrame，取第一行
        df = result.to_pandas()
        from tabulate import tabulate
        score_cols = [c for c in df.columns if c in VALID_METRICS]
        score_table = tabulate(
            df[score_cols].round(4).values.tolist(),
            headers=score_cols,
            tablefmt="simple",
            floatfmt=".4f",
        )
        logger.debug("Ragas 原始结果:\n{}", score_table)

        scores = {}
        for m in metric_names:
            if m in df.columns:
                val = df[m].iloc[0]
                scores[m] = round(float(val), 4) if val == val else 0.0  # NaN check

        elapsed = round(time.time() - start, 2)
        model_name = req.model or (AZURE_OAI_DEPLOYMENT if backend == "azure" else OLLAMA_MODEL)

        logger.success("Ragas 评估完成 | {elapsed}s | {scores}", elapsed=elapsed, scores=scores)

        return EvalResponse(
            scores=scores,
            details={
                "mode": "ragas (full pipeline)",
                "backend": backend,
                "model": model_name,
                "elapsed_seconds": elapsed,
                "metrics_used": metric_names,
            },
        )

    except ImportError as e:
        return EvalResponse(scores={}, error=f"依赖缺失: {e}")
    except Exception as e:
        logger.exception("Ragas 评估失败 | backend={}", backend)
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
    },
]

FAITHFULNESS_THRESHOLD = 0.5


class VerifyCaseResult(BaseModel):
    label: str
    case_type: str
    scores: dict[str, float]
    elapsed_seconds: float
    passed: bool  # 区分度检查
    question: str
    answer: str
    contexts: list[str]


class VerifyResponse(BaseModel):
    cases: list[VerifyCaseResult]
    all_passed: bool
    backend: str
    model: str
    total_elapsed: float


@router.post("/evaluation/verify", response_model=VerifyResponse)
async def run_verification(backend: str | None = None):
    """一键对比验证 — 3 组用例测试评估区分度"""
    be = backend or EVAL_BACKEND
    total_start = time.time()
    model_used = ""
    results: list[VerifyCaseResult] = []

    logger.info("对比验证开始 | backend={} | {} 组用例", be, len(VERIFY_CASES))

    for case in VERIFY_CASES:
        prompt = JUDGE_PROMPT.format(
            question=case["question"],
            answer=case["answer"],
            contexts="\n---\n".join(case["contexts"]),
            reference="（无参考答案）",
        )

        t0 = time.time()
        try:
            raw, model_used = (
                await _call_azure(prompt) if be == "azure"
                else await _call_ollama(prompt)
            )
            scores = _parse_judge_scores(raw)
        except Exception as e:
            logger.error("验证用例 {} 失败: {}", case["label"], e)
            scores = {"faithfulness": 0.0, "answer_relevancy": 0.0, "context_precision": 0.0}
        elapsed = round(time.time() - t0, 2)

        # 区分度检查
        faith = scores.get("faithfulness", 0.0)
        if case["type"] == "faithful":
            passed = faith > FAITHFULNESS_THRESHOLD
        else:
            passed = faith < FAITHFULNESS_THRESHOLD

        results.append(VerifyCaseResult(
            label=case["label"],
            case_type=case["type"],
            scores=scores,
            elapsed_seconds=elapsed,
            passed=passed,
            question=case["question"],
            answer=case["answer"],
            contexts=case["contexts"],
        ))
        logger.debug("  {} | faith={:.4f} | passed={} | {:.2f}s",
                      case["label"], faith, passed, elapsed)

    all_passed = all(r.passed for r in results)
    total_elapsed = round(time.time() - total_start, 2)

    status = "✅ 全部通过" if all_passed else "⚠️ 有失败项"
    logger.success("对比验证完成 | {} | {:.2f}s", status, total_elapsed)

    return VerifyResponse(
        cases=results,
        all_passed=all_passed,
        backend=be,
        model=model_used,
        total_elapsed=total_elapsed,
    )


# ═════════════════════════════════════════════════════════════
#  Info
# ═════════════════════════════════════════════════════════════

@router.get("/evaluation/info")
async def evaluation_info():
    return {
        "module": "ragas-evaluation",
        "active_backend": EVAL_BACKEND,
        "backends": {
            "azure": {"available": bool(AZURE_OAI_KEY), "model": AZURE_OAI_DEPLOYMENT},
            "ollama": {"available": True, "model": OLLAMA_MODEL},
        },
        "modes": {
            "quick": "/evaluation/quick — 单次调用 2-10s",
            "full": "/evaluation — Ragas 完整管道 15-60s",
            "verify": "/evaluation/verify — 3 组对比验证",
        },
        "available_metrics": list(VALID_METRICS),
    }
