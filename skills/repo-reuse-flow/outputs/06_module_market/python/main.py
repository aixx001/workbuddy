"""
Module Market — Python Demo API

结构: modules/<项目名>/<模块名>/
运行: uv run uvicorn main:app --reload --port 8100
"""

import logging
import sys

from loguru import logger

# ── 统一日志：把所有标准 logging 拦截到 loguru ──────────────


class _LoguruHandler(logging.Handler):
    """将标准 logging 事件转发到 loguru"""

    _LEVEL_MAP = {
        logging.DEBUG: "DEBUG",
        logging.INFO: "INFO",
        logging.WARNING: "WARNING",
        logging.ERROR: "ERROR",
        logging.CRITICAL: "CRITICAL",
    }

    def emit(self, record: logging.LogRecord):
        level = self._LEVEL_MAP.get(record.levelno, "INFO")
        # 过滤掉 uvicorn access log 的冗余细节
        if record.name == "uvicorn.access":
            # 简化: "POST /demo/ragas/evaluation 200" 而不是完整的
            msg = record.getMessage()
            # 去掉 IP 和 HTTP 版本，只保留 METHOD PATH STATUS
            import re
            m = re.search(r'"(\w+)\s+(\S+)\s+HTTP/[^"]*"\s+(\d+)', msg)
            if m:
                logger.log(level, "← {} {} {}", m.group(1), m.group(2), m.group(3))
                return
        logger.log(level, record.getMessage())


def _setup_logging():
    """配置全局日志"""
    # 移除 loguru 默认 handler，重新配置
    logger.remove()
    logger.add(
        sys.stderr,
        format=(
            "<green>{time:HH:mm:ss}</green> │ "
            "<level>{level: <7}</level> │ "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan> │ "
            "<level>{message}</level>"
        ),
        level="DEBUG",
        colorize=True,
    )

    # 拦截所有标准 logging（包括 uvicorn）
    handler = _LoguruHandler()
    logging.basicConfig(handlers=[handler], level=logging.INFO, force=True)

    # 显式替换 uvicorn 的 logger handler（basicConfig 不会覆盖已有的）
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        uv_logger = logging.getLogger(name)
        uv_logger.handlers.clear()
        uv_logger.addHandler(handler)
        uv_logger.propagate = False

    # 静默 httpx 的请求日志（太吵）
    logging.getLogger("httpx").setLevel(logging.WARNING)


_setup_logging()

# ── FastAPI App ──────────────────────────────────────────────

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from modules.ragas.evaluation import router as ragas_eval_router
from modules.ragas.question_gen import router as ragas_qgen_router
from modules.ragas.prompt import router as ragas_prompt_router
from modules.dspy.signatures import router as dspy_sig_router
from modules.deepeval.evaluation import router as deepeval_eval_router
from modules.promptfoo.config_gen import router as promptfoo_config_router

app = FastAPI(
    title="Module Market Demo API",
    description="模块功能演示服务 — 各模块 100% 使用源库 API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "service": "Module Market Demo API",
        "modules": {
            "ragas": [
                {"name": "evaluation", "endpoint": "/demo/ragas/evaluation", "method": "POST"},
                {"name": "question_gen", "endpoint": "/demo/ragas/question-gen", "method": "POST"},
                {"name": "prompt", "endpoint": "/demo/ragas/prompt", "method": "POST"},
            ],
            "dspy": [
                {"name": "signatures", "endpoint": "/demo/dspy/signatures", "method": "POST"},
            ],
            "deepeval": [
                {"name": "evaluation", "endpoint": "/demo/deepeval/evaluation", "method": "POST"},
            ],
            "promptfoo": [
                {"name": "config_gen", "endpoint": "/demo/promptfoo/generate-config", "method": "POST"},
            ],
        },
    }


# 按项目分组挂载路由
app.include_router(ragas_eval_router, prefix="/demo/ragas", tags=["ragas / Evaluation"])
app.include_router(ragas_qgen_router, prefix="/demo/ragas", tags=["ragas / Question Gen"])
app.include_router(ragas_prompt_router, prefix="/demo/ragas", tags=["ragas / Prompt"])
app.include_router(dspy_sig_router, prefix="/demo/dspy", tags=["dspy / Signatures"])
app.include_router(deepeval_eval_router, prefix="/demo/deepeval", tags=["deepeval / Evaluation"])
app.include_router(promptfoo_config_router, prefix="/demo/promptfoo", tags=["promptfoo / Config Gen"])

logger.info("Module Market Demo API 已就绪 | http://localhost:8100")
