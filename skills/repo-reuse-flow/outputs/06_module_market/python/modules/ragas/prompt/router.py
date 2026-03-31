"""
Prompt Framework Demo — 100% 使用 ragas PydanticPrompt

后端：azure (gpt-4o-mini) | ollama (本地)
模式：
  /prompt          — 渲染 prompt + 可选 LLM 调用
  /prompt/verify   — 3 组对比验证
"""

import json
import os
import time

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel as PydanticBaseModel

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
class PromptRequest(PydanticBaseModel):
    context: str
    topic: str = ""
    run_llm: bool = True  # 是否调用 LLM（默认调用）
    backend: str | None = None  # azure / ollama


class PromptResponse(PydanticBaseModel):
    rendered_prompt: str
    output: dict | None = None  # LLM 的结构化输出
    template_info: dict
    elapsed_seconds: float | None = None
    model: str | None = None
    error: str | None = None


# ═════════════════════════════════════════════════════════════
#  Ragas PydanticPrompt Schema 定义
# ═════════════════════════════════════════════════════════════

def _build_prompt_and_schema():
    """构建 ragas PydanticPrompt 实例和 IO schema"""
    from ragas.prompt import PydanticPrompt
    from pydantic import BaseModel

    class QuestionInput(BaseModel):
        context: str
        topic: str

    class QuestionOutput(BaseModel):
        question: str
        difficulty: str
        reasoning: str

    class GenerateQuestion(PydanticPrompt[QuestionInput, QuestionOutput]):
        instruction = "根据给定上下文和主题，生成一个教育性测试问题。返回问题、难度(easy/medium/hard)和推理理由。"
        input_model = QuestionInput
        output_model = QuestionOutput

    return GenerateQuestion, QuestionInput, QuestionOutput


# ═════════════════════════════════════════════════════════════
#  prompt 渲染 + LLM 调用
# ═════════════════════════════════════════════════════════════

@router.post("/prompt", response_model=PromptResponse)
async def run_prompt(req: PromptRequest):
    """使用 ragas PydanticPrompt 渲染结构化 prompt，可选调用 LLM"""
    backend = req.backend or EVAL_BACKEND
    start = time.time()

    try:
        GenerateQuestion, QuestionInput, QuestionOutput = _build_prompt_and_schema()

        prompt = GenerateQuestion()
        input_data = QuestionInput(context=req.context[:800], topic=req.topic)

        # Step 1: 渲染 prompt 文本（纯模板，不调 LLM）
        rendered = prompt.to_string(input_data)

        logger.info("Prompt 渲染完成 | topic={} | len={}", req.topic, len(rendered))

        # Step 2: 可选调用 LLM 获得结构化输出
        output = None
        model_used = None
        if req.run_llm:
            try:
                llm = _get_ragas_llm(backend)
                result = await prompt.generate(llm=llm, data=input_data)
                output = result.model_dump()
                model_used = (
                    AZURE_OAI_DEPLOYMENT if backend == "azure" else OLLAMA_MODEL
                )
                logger.success("LLM 调用成功 | model={}", model_used)
            except Exception as e:
                logger.error("LLM 调用失败: {}", e)
                output = {"error": str(e)}

        elapsed = round(time.time() - start, 2)

        return PromptResponse(
            rendered_prompt=rendered,
            output=output,
            elapsed_seconds=elapsed,
            model=model_used,
            template_info={
                "source": "ragas.prompt.PydanticPrompt",
                "input_schema": QuestionInput.model_json_schema(),
                "output_schema": QuestionOutput.model_json_schema(),
                "features": [
                    "Pydantic 类型约束 — 输出格式保证",
                    "instruction 自动注入 — 无需手写 system prompt",
                    "few-shot 支持 — 可添加示例提升质量",
                ],
            },
        )

    except ImportError as e:
        return PromptResponse(
            rendered_prompt="",
            template_info={},
            error=f"依赖缺失: {e}. 运行: uv add ragas",
        )
    except Exception as e:
        logger.exception("Prompt 模块异常")
        raise HTTPException(status_code=500, detail=str(e))


# ── LLM 构建 ─────────────────────────────────────────────────

def _get_ragas_llm(backend: str):
    from ragas.llms import LangchainLLMWrapper

    if backend == "azure":
        from langchain_openai import AzureChatOpenAI
        llm = AzureChatOpenAI(
            azure_endpoint=AZURE_OAI_ENDPOINT,
            api_key=AZURE_OAI_KEY,
            azure_deployment=AZURE_OAI_DEPLOYMENT,
            api_version=AZURE_OAI_API_VERSION,
            temperature=0,
        )
    else:
        from langchain_ollama import ChatOllama
        llm = ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0,
            num_ctx=4096,
            extra_body={"think": False},
        )
    return LangchainLLMWrapper(llm)


# ═════════════════════════════════════════════════════════════
#  对比验证 — 3 组用例一键对比
# ═════════════════════════════════════════════════════════════

VERIFY_CASES = [
    {
        "label": "✅ 科学主题",
        "type": "science",
        "context": (
            "光合作用（Photosynthesis）是植物、藻类和某些细菌利用光能"
            "将二氧化碳和水转化为葡萄糖和氧气的生化过程。"
            "光合作用主要发生在叶绿体中，包括光反应和暗反应两个阶段。"
        ),
        "topic": "生物学",
    },
    {
        "label": "✅ 技术主题",
        "type": "technical",
        "context": (
            "HNSW（Hierarchical Navigable Small World）是一种高效的近似最近邻搜索算法。"
            "它通过构建多层跳表结构的导航图来实现 O(log n) 的搜索复杂度。"
            "HNSW 广泛应用于向量数据库如 FAISS、Milvus 中。"
        ),
        "topic": "向量检索",
    },
    {
        "label": "❌ 空主题",
        "type": "no_topic",
        "context": "这是一段没有明确主题的随机文本。",
        "topic": "",
    },
]


class VerifyCaseResult(PydanticBaseModel):
    label: str
    case_type: str
    scores: dict[str, float | None]
    elapsed_seconds: float
    passed: bool
    rendered_length: int
    has_output: bool
    sample_question: str | None = None


class VerifyResponse(PydanticBaseModel):
    cases: list[VerifyCaseResult]
    all_passed: bool
    backend: str
    model: str
    total_elapsed: float


@router.post("/prompt/verify", response_model=VerifyResponse)
async def run_verification(backend: str | None = None):
    """一键对比验证 — 3 组用例测试 PydanticPrompt 渲染 + LLM 调用"""
    be = backend or EVAL_BACKEND
    total_start = time.time()
    model_used = AZURE_OAI_DEPLOYMENT if be == "azure" else OLLAMA_MODEL
    results: list[VerifyCaseResult] = []

    logger.info("对比验证开始 | backend={} | {} 组用例", be, len(VERIFY_CASES))

    for case in VERIFY_CASES:
        t0 = time.time()
        passed = False
        rendered_length = 0
        has_output = False
        sample_question = None
        scores: dict[str, float | None] = {}

        try:
            GenerateQuestion, QuestionInput, _ = _build_prompt_and_schema()
            prompt = GenerateQuestion()
            input_data = QuestionInput(context=case["context"], topic=case["topic"])

            # 渲染（必须成功）
            rendered = prompt.to_string(input_data)
            rendered_length = len(rendered)
            render_ok = rendered_length > 50  # 合理的 prompt 长度

            # LLM 调用
            llm = _get_ragas_llm(be)
            result = await prompt.generate(llm=llm, data=input_data)
            output = result.model_dump()

            has_output = bool(output.get("question"))
            sample_question = output.get("question", "")[:80]

            # 质量检查
            has_difficulty = output.get("difficulty", "") in ("easy", "medium", "hard")
            has_reasoning = len(output.get("reasoning", "")) > 5

            scores = {
                "render_ok": 1.0 if render_ok else 0.0,
                "has_question": 1.0 if has_output else 0.0,
                "has_difficulty": 1.0 if has_difficulty else 0.0,
                "has_reasoning": 1.0 if has_reasoning else 0.0,
            }

            # 正常主题：4 项全通过；空主题：渲染成功 + 有问题即可
            if case["type"] == "no_topic":
                passed = render_ok and has_output
            else:
                passed = render_ok and has_output and has_difficulty and has_reasoning

        except Exception as e:
            logger.error("验证用例 {} 失败: {}", case["label"], e)
            scores = {
                "render_ok": 1.0 if rendered_length > 50 else 0.0,
                "has_question": 0.0,
                "has_difficulty": 0.0,
                "has_reasoning": 0.0,
            }

        elapsed = round(time.time() - t0, 2)

        results.append(VerifyCaseResult(
            label=case["label"],
            case_type=case["type"],
            scores=scores,
            elapsed_seconds=elapsed,
            passed=passed,
            rendered_length=rendered_length,
            has_output=has_output,
            sample_question=sample_question,
        ))
        logger.debug("  {} | render={} | output={} | passed={} | {:.2f}s",
                      case["label"], rendered_length, has_output, passed, elapsed)

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

@router.get("/prompt/info")
async def prompt_info():
    return {
        "module": "ragas-prompt",
        "active_backend": EVAL_BACKEND,
        "backends": {
            "azure": {"available": bool(AZURE_OAI_KEY), "model": AZURE_OAI_DEPLOYMENT},
            "ollama": {"available": True, "model": OLLAMA_MODEL},
        },
        "source_library": "ragas.prompt",
        "template_types": [
            {"name": "pydantic", "class": "PydanticPrompt", "description": "Pydantic 结构化 — 类型安全"},
            {"name": "few_shot", "class": "FewShotPydanticPrompt", "description": "Few-shot + 结构化"},
            {"name": "dynamic", "class": "DynamicFewShotPrompt", "description": "动态选择最相关示例"},
        ],
    }
