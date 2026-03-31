# Step 1: 需求收集 (demand)

**触发条件**: `outputs/01_demand/demand.json` 不存在或为空

## 执行步骤

1. 与用户对话，收集以下信息：
   - **业务目标**: 你在做什么项目？想解决什么问题？
   - **现有技术栈**: Python/Node？用了什么框架？
   - **技术约束**: 必须用本地模型？有 GPU 吗？
   - **目标功能**: 需要什么能力？(RAG、评估、问答生成...)

2. 运行需求收集脚本：
   ```bash
   .venv\Scripts\python.exe scripts/01_demand_collect.py
   ```

3. 生成 `outputs/01_demand/demand.json`

## 完成检查

- [ ] `outputs/01_demand/demand.json` 存在
- [ ] JSON 包含 `keywords` 和 `constraints` 字段

## 产出格式

```json
{
  "project": "textbook-rag",
  "keywords": ["RAG", "evaluation", "question-generation"],
  "constraints": {
    "language": "python",
    "local_model": true,
    "frameworks": ["fastapi", "langchain"]
  }
}
```
