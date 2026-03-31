# Step 6: 模块上架 (market)

**触发条件**: 无验证脚本或验证未通过

**加载 Skill**: `skills/module-demo-builder`

## 五步走：读 → 试 → 验 → 评 → 拿

每个模块必须走完全部 5 步才算上架完成。

### Step 6a — 读（moduleContent + seed）

1. `seed-modules.ts` 写好模块元数据（description、tags、integrationGuide、apiReference）
2. `_components/constants.tsx` 添加 `moduleContent` 配置：
   - `problem` — 这个模块解决什么问题
   - `fitCriteria` — 适合你如果…（3 条）
   - `demoTitle` / `demoScenario` — 场景化演示标题
   - `inputLabels` — 输入字段的中文标签
   - `resultInterpretation` — 各指标的中文解读

### Step 6b — 试（router + demo endpoint）

1. **⚠️ 先看源项目 — 不准凭印象写代码**
   - 参考项目已 clone 到：`outputs/03_analysis/cloned/<project>/`
   - 抽取的模块在：`outputs/05_modules/extracted_modules/`
   - **必须先读源码**确认 API 参数、必填字段、分数含义（例：HallucinationMetric 需要 `context` 不是 `retrieval_context`）
   - 确认所有核心类、指标、函数都覆盖到
   - 例：DeepEval 有 `FaithfulnessMetric` / `HallucinationMetric` / `AnswerRelevancyMetric` / `GEval` → 4 个全上
   - 例：Ragas 有 `faithfulness` / `answer_relevancy` / `context_precision` → 3 个全上
2. `modules/<project>/<feature>/router.py` 实现核心 API
3. router 100% 调用源库 API（不自己实现逻辑）
4. **⚠️ 必须覆盖源库的所有核心 API**（不能只挑 2 个测。一个模块有 4 个指标就必须 4 个全上）
5. `main.py` 挂载路由，前端 Demo 可正常调用
6. `seed-modules.ts` 设置 `demoEndpoint` + `demoPayload`

### Step 6c — 验（verify script + /verify endpoint）

1. 生成 `python/workflows/verify_<module>.py`
2. 设计 3+ 组对比用例（忠实 / 幻觉 / 跑题）
3. **验证脚本必须测试所有已实现的指标** — 不能只测一部分
4. **⚠️ 脚本输出必须保存到 `python/results/` 目录** — 终端会截断且中文乱码，不可信
   - 验证结果保存到 `python/results/verify_<module>.json`
   - 用 `view_file` 读文件确认分数，**不要看终端输出**
   - **Windows PowerShell 中文乱码解决方案**：
     - 脚本内所有文件写入必须用 `encoding="utf-8"`
     - 运行时设置 `$env:PYTHONUTF8=1`（比 PYTHONIOENCODING 更可靠）
     - **永远不要信任终端中文输出**，只看保存的 JSON 文件
5. **运行验证，全部 PASS 才继续**：
   ```powershell
   cd outputs/06_module_market/python
   $env:PYTHONUTF8=1
   .venv\Scripts\python.exe workflows\verify_<module>.py
   # 然后用 view_file 读取保存的 JSON 文件确认结果
   ```
6. router.py 添加 `/verify` 端点
7. 前端添加 "验" tab，调用 verify 端点

### Step 6d — 评（evaluation record）

**基于实际脚本运行的结果，生成正式评估记录。**

1. 保存评估记录到 `python/results/eval_<module>.json`（与 verify 结果在同一目录）
2. 记录内容：
   - `module` — 模块 slug
   - `backend` — 评估用的 LLM 后端
   - `cases` — 各测试用例的分数 + pass/fail
   - `all_passed` — 是否全部通过
   - `total_elapsed` — 总耗时
   - `evaluated_at` — 评估时间
   - `verdict` — 结论（可用 / 有风险 / 不可用）
3. 前端 "评" tab 展示评估报告
4. `_components/constants.tsx` 中的 `evaluationRecords` 保存前端展示用的评估数据
5. **只有评估结论为"可用"的模块才标记 status: active**

### Step 6e — 拿（installation guide）

1. 前端 "拿" tab 展示安装命令 + 源码链接
2. integrationGuide 可复制
3. 安装型: `pip install <package>`
4. 提取型: 文件列表 + 依赖说明

## 完成检查

- [ ] `moduleContent` 配置完整（problem + fitCriteria）
- [ ] Demo 可正常运行
- [ ] `workflows/verify_<module>.py` 全部 PASS（退出码 0）
- [ ] `results/verify_<module>.json` 存在且 `all_passed: true`
- [ ] `results/eval_<module>.json` 存在且 `verdict: 可用`
- [ ] 前端 5 个 tab 全部可用
