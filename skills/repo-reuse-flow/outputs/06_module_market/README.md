# Module Market

模块市场 — 从开源项目中提取功能模块，测试验证后迁移到目标项目。

## 目录结构

```
06_module_market/
├── payload/                    # Payload CMS + Next.js 前端
│   ├── src/
│   │   ├── collections/        #   数据模型 (Modules, Repos, Versions)
│   │   ├── app/(frontend)/     #   模块市场前端
│   │   │   ├── page.tsx        #     入口 (45行路由 shell)
│   │   │   └── _components/    #     拆分后的组件 (14个文件)
│   │   │       ├── constants.tsx   # 类型 + 常量 + 静态数据
│   │   │       ├── hooks.ts       # 自定义 hooks
│   │   │       ├── tabs/          # 5 个详情 Tab
│   │   │       └── ...            # 页面 + 侧边栏 + 卡片组件
│   │   └── seed/               #   数据初始化脚本
│   └── package.json
│
├── python/                     # Python Demo API (FastAPI)
│   ├── main.py                 #   API 入口 (port 8100)
│   ├── modules/                #   按项目分组的模块
│   │   ├── ragas/              #     Ragas 评估框架
│   │   ├── deepeval/           #     DeepEval 评估框架
│   │   └── dspy/               #     DSPy Signatures
│   ├── workflows/              #   验证脚本 (verify_*.py)
│   ├── results/                #   验证 + 评估结果 (唯一数据输出)
│   └── pyproject.toml          #   uv 管理的依赖
│
└── README.md
```

## 核心原则

1. **100% 源库 API** — router.py 只做 HTTP 包装，核心逻辑全部调用原始开源库
2. **溯源清晰** — 每个模块的 meta.json 记录来自哪个开源项目、哪个子模块、license
3. **独立可迁移** — 每个模块目录可以整体复制到目标项目

## 启动

### 1. Python Demo API

```bash
cd python
uv sync                                          # 安装依赖
uv run uvicorn main:app --reload --port 8100      # → http://localhost:8100
```

需要设置 `OPENAI_API_KEY` 环境变量（评估和生成都需要 LLM）。

### 2. Payload CMS + 前端

```bash
cd payload
pnpm install
pnpm dev                                          # → http://localhost:3000
```

### 3. Seed 数据

```bash
# 确保 Payload 在跑 (localhost:3000)
cd payload
npx tsx src/seed/seed-modules.ts
```

## 模块类型

| 类型 | 说明 | 示例 |
|------|------|------|
| **📦 安装型** | `pip install` 直接用，router.py 调原库 API | ragas, deepeval |
| **🔧 提取型** | 代码提取到项目，在 `05_modules/extracted_modules/` | ragflow_common |

## 添加新模块

1. 在 `python/modules/<项目名>/` 下建模块目录
2. 写 `meta.json`（溯源信息）
3. 写 `router.py`（FastAPI 路由，只调原库 API）
4. 在 `main.py` 中挂载路由
5. 在 Payload seed 脚本中添加模块数据
