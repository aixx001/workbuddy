#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
import base64

from .core_container import _CONTAINER_EXECUTION_SEMAPHORES
from .core_logger import logger
from fastapi import Request
from .models_enums import ResultStatus, SupportLanguage
from .models_schemas import CodeExecutionRequest, CodeExecutionResult
from .services_execution import execute_code
from .services_limiter import limiter
from .services_security import analyze_code_security


async def healthz_handler():
    return {"status": "ok"}


@limiter.limit("5/second")
async def run_code_handler(req: CodeExecutionRequest, request: Request):
    logger.info("🟢 Received /run request")

    async with _CONTAINER_EXECUTION_SEMAPHORES[req.language]:
        code = base64.b64decode(req.code_b64).decode("utf-8")
        if req.language == SupportLanguage.NODEJS:
            code += "\n\nmodule.exports = { main };"
            req.code_b64 = base64.b64encode(code.encode("utf-8")).decode("utf-8")
        is_safe, issues = analyze_code_security(code, language=req.language)
        if not is_safe:
            issue_details = "\n".join([f"Line {lineno}: {issue}" for issue, lineno in issues])
            return CodeExecutionResult(status=ResultStatus.PROGRAM_RUNNER_ERROR, stdout="", stderr=issue_details, exit_code=-999, detail="Code is unsafe")

        try:
            return await execute_code(req)
        except Exception as e:
            return CodeExecutionResult(status=ResultStatus.PROGRAM_RUNNER_ERROR, stdout="", stderr=str(e), exit_code=-999, detail="unhandled_exception")
