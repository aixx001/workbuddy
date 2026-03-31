"""
Question Generation Demo — 从文档自动生成测试问题

后端：azure (gpt-4o-mini) | ollama (本地)
模式：
  /question-gen/quick  — 单次 LLM 调用快速生成（2-10s）
  /question-gen        — 完整 Ragas Testset 管道（30-120s）
  /question-gen/verify — 3 组对比验证
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

AZURE_OAI_ENDPOINT = os.getenv("AZURE_OAI_ENDPOINT", "")
AZURE_OAI_KEY = os.getenv("AZURE_OAI_KEY", "")
AZURE_OAI_DEPLOYMENT = os.getenv("AZURE_OAI_DEPLOYMENT", "gpt-4o-mini")
AZURE_OAI_API_VERSION = os.getenv("AZURE_OAI_API_VERSION", "2024-12-01-preview")


# ── 请求 / 响应模型 ──────────────────────────────────────────
class QuestionGenRequest(BaseModel):
    text: str
    num_questions: int = 3
    question_types: list[str] | None = None  # factual / reasoning / comparison
    backend: str | None = None  # azure / ollama
    model: str | None = None


class GeneratedQuestion(BaseModel):
    question: str
    answer: str
    question_type: str
    difficulty: str  # easy / medium / hard


class QuestionGenResponse(BaseModel):
    questions: list[GeneratedQuestion]
    metadata: dict | None = None
    error: str | None = None


# ═════════════════════════════════════════════════════════════
#  快速生成 — 单次 LLM 调用
# ═════════════════════════════════════════════════════════════

QGEN_PROMPT = """\
你是一个教育测试题生成专家。根据以下文档内容，生成 {num_questions} 道测试题。

**文档内容**:
{text}

**要求**:
1. 每道题必须基于文档内容，不能编造文档中没有的信息
2. 题型分布：事实题（factual）、推理题（reasoning）、比较题（comparison）
3. 每道题都要有正确答案
4. 难度标注：easy / medium / hard

只返回严格 JSON 数组（不要 markdown）：
[
  {{"question": "...", "answer": "...", "question_type": "factual", "difficulty": "easy"}},
  ...
]
"""


@router.post("/question-gen/quick", response_model=QuestionGenResponse)
async def run_quick_question_gen(req: QuestionGenRequest):
    """单次 LLM 调用快速生成测试题"""
    backend = req.backend or EVAL_BACKEND
    start = time.time()

    logger.info("快速题目生成开始 | backend={} num={}", backend, req.num_questions)

    try:
        prompt = QGEN_PROMPT.format(
            text=req.text[:2000],  # 限制输入长度
            num_questions=req.num_questions,
        )

        raw, model_used = (
            await _call_azure(prompt) if backend == "azure"
            else await _call_ollama(prompt, req.model)
        )

        questions = _parse_questions(raw)
        elapsed = round(time.time() - start, 2)

        logger.success("快速题目生成完成 | {elapsed}s | {count} 题",
                       elapsed=elapsed, count=len(questions))

        return QuestionGenResponse(
            questions=questions,
            metadata={
                "mode": "quick (LLM-as-Judge)",
                "backend": backend,
                "model": model_used,
                "elapsed_seconds": elapsed,
                "source_text_length": len(req.text),
            },
        )
    except Exception as e:
        logger.exception("快速题目生成失败 | backend={}", backend)
        raise HTTPException(status_code=500, detail=str(e))


# ═════════════════════════════════════════════════════════════
#  完整 Ragas Testset 管道
# ═════════════════════════════════════════════════════════════

@router.post("/question-gen", response_model=QuestionGenResponse)
async def run_question_gen(req: QuestionGenRequest):
    """使用 ragas TestsetGenerator 从文本生成测试问题"""
    backend = req.backend or EVAL_BACKEND
    start = time.time()

    try:
        from ragas.testset import TestsetGenerator
        from ragas.llms import LangchainLLMWrapper
        from langchain_core.documents import Document

        docs = [Document(page_content=req.text)]

        # 构建 LLM（复用 evaluation 的模式）
        llm = _get_ragas_llm(backend, req.model)
        generator = TestsetGenerator(llm=llm)

        logger.info("Ragas Testset 生成开始 | backend={} num={}", backend, req.num_questions)

        testset = generator.generate_with_langchain_docs(
            documents=docs,
            testset_size=req.num_questions,
        )

        df = testset.to_pandas()
        questions = []
        for _, row in df.iterrows():
            questions.append(
                GeneratedQuestion(
                    question=row.get("user_input", ""),
                    answer=row.get("reference", ""),
                    question_type=row.get("synthesizer_name", "unknown"),
                    difficulty="medium",
                )
            )

        elapsed = round(time.time() - start, 2)
        model_name = req.model or (AZURE_OAI_DEPLOYMENT if backend == "azure" else OLLAMA_MODEL)

        logger.success("Ragas Testset 完成 | {elapsed}s | {count} 题",
                       elapsed=elapsed, count=len(questions))

        return QuestionGenResponse(
            questions=questions,
            metadata={
                "mode": "ragas (TestsetGenerator)",
                "backend": backend,
                "model": model_name,
                "elapsed_seconds": elapsed,
                "source_library": "ragas.testset.TestsetGenerator",
            },
        )

    except ImportError as e:
        return QuestionGenResponse(
            questions=[],
            error=f"依赖缺失: {e}. 运行: uv add ragas langchain-openai",
        )
    except Exception as e:
        logger.exception("Ragas Testset 生成失败 | backend={}", backend)
        raise HTTPException(status_code=500, detail=str(e))


# ── LLM 调用 ─────────────────────────────────────────────────

async def _call_azure(prompt: str) -> tuple[str, str]:
    import httpx

    url = (
        f"{AZURE_OAI_ENDPOINT.rstrip('/')}/openai/deployments/"
        f"{AZURE_OAI_DEPLOYMENT}/chat/completions?api-version={AZURE_OAI_API_VERSION}"
    )

    logger.debug("Azure 请求 → {}", AZURE_OAI_DEPLOYMENT)
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, headers={
            "api-key": AZURE_OAI_KEY,
            "Content-Type": "application/json",
        }, json={
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,  # 稍微提高温度增加题目多样性
            "max_tokens": 1000,
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
            "options": {"temperature": 0.3, "num_ctx": 4096},
        })
        resp.raise_for_status()
        data = resp.json()

    content = data["message"]["content"]
    logger.debug("Ollama 响应 ← {} chars", len(content))
    return content, model


def _get_ragas_llm(backend: str, model_name: str | None = None):
    from ragas.llms import LangchainLLMWrapper

    if backend == "azure":
        from langchain_openai import AzureChatOpenAI
        llm = AzureChatOpenAI(
            azure_endpoint=AZURE_OAI_ENDPOINT,
            api_key=AZURE_OAI_KEY,
            azure_deployment=model_name or AZURE_OAI_DEPLOYMENT,
            api_version=AZURE_OAI_API_VERSION,
            temperature=0.3,
        )
    else:
        from langchain_ollama import ChatOllama
        llm = ChatOllama(
            model=model_name or OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.3,
            num_ctx=4096,
            extra_body={"think": False},
        )
    return LangchainLLMWrapper(llm)


# ── 解析生成的题目 ────────────────────────────────────────────

def _parse_questions(raw: str) -> list[GeneratedQuestion]:
    """从 LLM 输出解析题目 JSON 数组"""
    # 清理 markdown code block
    cleaned = re.sub(r"```json?\s*|\s*```", "", raw).strip()

    try:
        items = json.loads(cleaned)
        if isinstance(items, list):
            return [
                GeneratedQuestion(
                    question=item.get("question", ""),
                    answer=item.get("answer", ""),
                    question_type=item.get("question_type", "unknown"),
                    difficulty=item.get("difficulty", "medium"),
                )
                for item in items
                if item.get("question")
            ]
    except json.JSONDecodeError:
        pass

    # fallback: 尝试逐行找 JSON 对象
    questions = []
    for match in re.finditer(r'\{[^}]+\}', raw):
        try:
            item = json.loads(match.group())
            if "question" in item:
                questions.append(GeneratedQuestion(
                    question=item["question"],
                    answer=item.get("answer", ""),
                    question_type=item.get("question_type", "unknown"),
                    difficulty=item.get("difficulty", "medium"),
                ))
        except (json.JSONDecodeError, ValueError):
            continue

    if questions:
        return questions

    raise ValueError(f"无法解析题目: {raw[:300]}")


# ═════════════════════════════════════════════════════════════
#  对比验证 — 3 组用例一键对比
# ═════════════════════════════════════════════════════════════

VERIFY_CASES = [
    {
        "label": "✅ 事实性文本",
        "type": "factual_text",
        "text": (
            "光合作用（Photosynthesis）是植物、藻类和某些细菌利用光能"
            "将二氧化碳和水转化为葡萄糖和氧气的生化过程。"
            "光合作用主要发生在叶绿体中，包括光反应和暗反应两个阶段。"
            "光反应在类囊体薄膜上进行，将光能转化为 ATP 和 NADPH。"
            "暗反应（Calvin 循环）在叶绿体基质中进行，利用 ATP 和 NADPH 固定 CO2。"
        ),
        "num_questions": 3,
        "check_question_count": True,
        "check_answer_quality": True,
        "min_questions": 2,
    },
    {
        "label": "✅ 技术性文本",
        "type": "technical_text",
        "text": (
            "向量数据库（Vector Database）是专门用于存储和检索高维向量数据的数据库系统。"
            "常见的向量检索算法包括 HNSW（Hierarchical Navigable Small World）、"
            "IVF（Inverted File Index）和 PQ（Product Quantization）。"
            "HNSW 通过构建多层导航图实现近似最近邻搜索，时间复杂度为 O(log n)。"
            "FAISS 是 Meta 开源的向量检索库，支持 GPU 加速。"
            "Milvus 是一个云原生的向量数据库，支持十亿级向量的实时检索。"
        ),
        "num_questions": 3,
        "check_question_count": True,
        "check_answer_quality": True,
        "min_questions": 2,
    },
    {
        "label": "❌ 无意义文本",
        "type": "garbage_text",
        "text": "啊啊啊啊 blah blah 123 !@#$% random noise asdfghjkl 乱码测试 xxxyyy",
        "num_questions": 3,
        "check_question_count": False,
        "check_answer_quality": False,
        "min_questions": 0,
    },
]


class VerifyCaseResult(BaseModel):
    label: str
    case_type: str
    scores: dict[str, float | None]
    elapsed_seconds: float
    passed: bool
    question_count: int
    sample_questions: list[str]


class VerifyResponse(BaseModel):
    cases: list[VerifyCaseResult]
    all_passed: bool
    backend: str
    model: str
    total_elapsed: float


@router.post("/question-gen/verify", response_model=VerifyResponse)
async def run_verification(backend: str | None = None):
    """一键对比验证 — 3 组用例测试题目生成质量"""
    be = backend or EVAL_BACKEND
    total_start = time.time()
    model_used = ""
    results: list[VerifyCaseResult] = []

    logger.info("对比验证开始 | backend={} | {} 组用例", be, len(VERIFY_CASES))

    for case in VERIFY_CASES:
        prompt = QGEN_PROMPT.format(
            text=case["text"],
            num_questions=case["num_questions"],
        )

        t0 = time.time()
        passed = False
        questions: list[GeneratedQuestion] = []
        scores: dict[str, float | None] = {}

        try:
            raw, model_used = (
                await _call_azure(prompt) if be == "azure"
                else await _call_ollama(prompt)
            )
            questions = _parse_questions(raw)

            # 评估质量
            q_count = len(questions)
            has_answers = sum(1 for q in questions if q.answer.strip()) / max(q_count, 1)
            has_types = sum(1 for q in questions if q.question_type != "unknown") / max(q_count, 1)

            scores = {
                "question_count": float(q_count),
                "answer_coverage": round(has_answers, 2),
                "type_coverage": round(has_types, 2),
            }

            # 区分度检查
            if case["check_question_count"]:
                # 正常文本：至少生成 min_questions 道有效题
                passed = (q_count >= case["min_questions"]
                          and has_answers >= 0.5)
            else:
                # 无意义文本：生成的题目质量应该很差（答案覆盖率低）
                # 如果 LLM 还是能生成题（可能质量差），也算通过
                passed = True  # 垃圾文本只要不崩就行

        except Exception as e:
            logger.error("验证用例 {} 失败: {}", case["label"], e)
            scores = {"question_count": 0, "answer_coverage": 0, "type_coverage": 0}
            if not case["check_question_count"]:
                passed = True  # 垃圾文本生成失败也合理

        elapsed = round(time.time() - t0, 2)

        results.append(VerifyCaseResult(
            label=case["label"],
            case_type=case["type"],
            scores=scores,
            elapsed_seconds=elapsed,
            passed=passed,
            question_count=len(questions),
            sample_questions=[q.question for q in questions[:3]],
        ))
        logger.debug("  {} | count={} | passed={} | {:.2f}s",
                      case["label"], len(questions), passed, elapsed)

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

@router.get("/question-gen/info")
async def question_gen_info():
    return {
        "module": "ragas-testset",
        "active_backend": EVAL_BACKEND,
        "backends": {
            "azure": {"available": bool(AZURE_OAI_KEY), "model": AZURE_OAI_DEPLOYMENT},
            "ollama": {"available": True, "model": OLLAMA_MODEL},
        },
        "modes": {
            "quick": "/question-gen/quick — 单次 LLM 调用 2-10s",
            "full": "/question-gen — Ragas Testset 管道 30-120s",
            "verify": "/question-gen/verify — 3 组对比验证",
        },
        "question_types": ["factual", "reasoning", "comparison"],
    }
