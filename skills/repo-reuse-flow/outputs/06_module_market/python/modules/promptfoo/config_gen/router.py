"""
Promptfoo Config Generator Demo

POST /demo/promptfoo/generate-config
{
    "prompt_template": "你是一个教育助手...",
    "test_cases": [
        {"question": "什么是光合作用？", "expected_keywords": ["光能", "植物"]}
    ],
    "models": ["gpt-4o-mini", "gpt-3.5-turbo"]
}

返回: 可直接使用的 promptfooconfig.yaml 内容
"""

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class TestCaseInput(BaseModel):
    question: str
    expected_keywords: list[str] = []
    context: str = ""


class PromptfooRequest(BaseModel):
    prompt_template: str = "你是一个教育助手。根据上下文回答问题。\n上下文: {{context}}\n问题: {{question}}"
    test_cases: list[TestCaseInput] = []
    models: list[str] = ["openai:gpt-4o-mini"]


class PromptfooResponse(BaseModel):
    yaml_config: str
    config_dict: dict
    run_command: str
    error: str | None = None


@router.post("/generate-config", response_model=PromptfooResponse)
async def generate_config(req: PromptfooRequest):
    """生成 promptfoo 评估配置"""
    try:
        config: dict = {
            "prompts": [req.prompt_template],
            "providers": req.models if req.models else ["openai:gpt-4o-mini"],
            "tests": [],
        }

        for tc in req.test_cases:
            test_entry: dict = {
                "vars": {"question": tc.question},
            }
            if tc.context:
                test_entry["vars"]["context"] = tc.context

            assertions = []
            for kw in tc.expected_keywords:
                assertions.append({"type": "contains", "value": kw})

            if assertions:
                test_entry["assert"] = assertions

            config["tests"].append(test_entry)

        # 如果没有测试用例，加个示例
        if not config["tests"]:
            config["tests"] = [
                {
                    "vars": {
                        "question": "什么是光合作用？",
                        "context": "光合作用是植物利用光能将CO2和H2O转化为有机物的过程。",
                    },
                    "assert": [
                        {"type": "contains", "value": "光能"},
                        {"type": "llm-rubric", "value": "回答准确且适合学生理解"},
                    ],
                }
            ]

        yaml_str = yaml.dump(config, allow_unicode=True, default_flow_style=False, sort_keys=False)

        return PromptfooResponse(
            yaml_config=yaml_str,
            config_dict=config,
            run_command="npx promptfoo eval && npx promptfoo view",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═════════════════════════════════════════════════════════════
#  对比验证 — 3 组用例一键对比
# ═════════════════════════════════════════════════════════════

VERIFY_CASES = [
    {
        "label": "✅ 完整配置 — 多模型 + 多用例 + 断言",
        "type": "complete",
        "payload": {
            "prompt_template": "你是一个教育助手。根据上下文回答问题。\n上下文: {{context}}\n问题: {{question}}",
            "test_cases": [
                {"question": "什么是光合作用？", "expected_keywords": ["光能", "植物", "二氧化碳"],
                 "context": "光合作用是植物利用光能将CO2和H2O转化为有机物的过程。"},
                {"question": "牛顿第三定律是什么？", "expected_keywords": ["作用力", "反作用力"],
                 "context": "牛顿第三定律：两个物体之间的作用力和反作用力大小相等、方向相反。"},
            ],
            "models": ["openai:gpt-4o-mini", "openai:gpt-3.5-turbo"],
        },
        "check_tests": 2,
        "check_providers": 2,
        "check_has_asserts": True,
    },
    {
        "label": "✅ 最小配置 — 空用例自动补默认",
        "type": "minimal",
        "payload": {
            "prompt_template": "回答问题：{{question}}",
            "test_cases": [],
            "models": ["openai:gpt-4o-mini"],
        },
        "check_tests": 1,  # 空 → 自动补 1 个
        "check_providers": 1,
        "check_has_asserts": True,
    },
    {
        "label": "✅ 中文场景 — 关键词断言正确生成",
        "type": "chinese",
        "payload": {
            "prompt_template": "你是一个中文阅读理解助手。\n原文: {{context}}\n问题: {{question}}",
            "test_cases": [
                {"question": "鲁迅的代表作是什么？",
                 "expected_keywords": ["呐喊", "狂人日记"],
                 "context": "鲁迅（1881-1936），原名周树人，代表作有《呐喊》《彷徨》等。"},
            ],
            "models": ["openai:gpt-4o-mini"],
        },
        "check_tests": 1,
        "check_providers": 1,
        "check_has_asserts": True,
    },
]


class VerifyCaseResult(BaseModel):
    label: str
    case_type: str
    tests_count: int
    providers_count: int
    yaml_valid: bool
    has_asserts: bool
    elapsed_seconds: float
    passed: bool
    pass_reason: str


class VerifyResponse(BaseModel):
    cases: list[VerifyCaseResult]
    all_passed: bool
    total_elapsed: float


@router.post("/generate-config/verify", response_model=VerifyResponse)
async def run_verification():
    """一键对比验证 — 3 组用例测试配置生成正确性"""
    import time as _time
    total_start = _time.time()
    results: list[VerifyCaseResult] = []

    for case in VERIFY_CASES:
        t0 = _time.time()
        passed = False
        pass_reason = ""
        tests_count = 0
        providers_count = 0
        yaml_valid = False
        has_asserts = False

        try:
            # 直接调用自己的生成逻辑（不走 HTTP）
            req = PromptfooRequest(**case["payload"])
            resp = await generate_config(req)

            # 解析结果
            yaml_valid = _is_valid_yaml(resp.yaml_config)
            tests_count = len(resp.config_dict.get("tests", []))
            providers_count = len(resp.config_dict.get("providers", []))
            has_asserts = any(
                t.get("assert") for t in resp.config_dict.get("tests", [])
            )

            # 区分度检查
            checks = [
                yaml_valid,
                tests_count >= case["check_tests"],
                providers_count >= case["check_providers"],
            ]
            if case["check_has_asserts"]:
                checks.append(has_asserts)

            passed = all(checks)
            if not passed:
                reasons = []
                if not yaml_valid:
                    reasons.append("YAML 无效")
                if tests_count < case["check_tests"]:
                    reasons.append(f"测试用例数 {tests_count} < {case['check_tests']}")
                if providers_count < case["check_providers"]:
                    reasons.append(f"Provider 数 {providers_count} < {case['check_providers']}")
                if case["check_has_asserts"] and not has_asserts:
                    reasons.append("缺少断言")
                pass_reason = "失败: " + "; ".join(reasons)
            else:
                pass_reason = f"配置正确: {tests_count} tests, {providers_count} providers, 有断言"

        except Exception as e:
            pass_reason = f"调用失败: {e}"

        elapsed = round(_time.time() - t0, 2)
        results.append(VerifyCaseResult(
            label=case["label"],
            case_type=case["type"],
            tests_count=tests_count,
            providers_count=providers_count,
            yaml_valid=yaml_valid,
            has_asserts=has_asserts,
            elapsed_seconds=elapsed,
            passed=passed,
            pass_reason=pass_reason,
        ))

    all_passed = all(r.passed for r in results)
    total_elapsed = round(_time.time() - total_start, 2)

    return VerifyResponse(
        cases=results,
        all_passed=all_passed,
        total_elapsed=total_elapsed,
    )


def _is_valid_yaml(yaml_str: str) -> bool:
    """检查 YAML 字符串是否合法"""
    try:
        obj = yaml.safe_load(yaml_str)
        return isinstance(obj, dict)
    except Exception:
        return False


# ═════════════════════════════════════════════════════════════
#  Info
# ═════════════════════════════════════════════════════════════

@router.get("/generate-config/info")
async def promptfoo_info():
    return {
        "module": "promptfoo",
        "description": "生成 promptfoo YAML 配置文件，用于 A/B 测试和多模型对比",
        "features": [
            "多模型 A/B 对比",
            "YAML 配置",
            "断言验证 (contains, llm-rubric, similar)",
            "CI/CD 集成",
        ],
        "modes": {
            "generate-config": "/generate-config — 生成 YAML 配置",
            "verify": "/generate-config/verify — 3 组对比验证",
        },
    }
