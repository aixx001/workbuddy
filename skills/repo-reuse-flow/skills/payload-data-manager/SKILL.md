---
name: payload-data-manager
description: |
  Manage Payload CMS data for Module Market. Handles seeding, updating, schema validation,
  and status transitions. Single source of truth for all CMS data operations.
  Triggers: 更新数据, seed, 上架数据, 模块数据, payload数据, CMS数据
description_zh: "Module Market Payload CMS 数据管理"
description_en: "Manage Payload CMS data for Module Market"
---

# Payload Data Manager

Module Market 的 Payload CMS 数据管理工具。所有数据变更必须通过这个 skill。

## 核心原则

> **唯一入口**: 所有 CMS 数据操作（增/改/查/删）通过 `scripts/payload_api.py` 统一处理。
> **不再手动跑 seed**: 用 Python 脚本直接调 Payload REST API，避免 TypeScript 编译问题。

## 使用场景

| 场景 | 命令 |
|------|------|
| 查看所有模块状态 | `python scripts/payload_api.py list` |
| 更新单个模块状态 | `python scripts/payload_api.py update-status <slug> active` |
| 上架新模块 | `python scripts/payload_api.py upsert-module <slug>` |
| 同步 seed 数据 | `python scripts/payload_api.py sync-all` |
| 查看 schema | `python scripts/payload_api.py schema` |

## 目录结构

```
payload-data-manager/
├── SKILL.md              # ← 你在这里
└── scripts/
    └── payload_api.py    # 统一 API 客户端
```

## 状态流转

```
draft → testing → active → published → archived
                    ↑
                    └── 验证脚本全 PASS + 评估结论"可用" 才能到 active
```

### 状态含义

| 状态 | 含义 | 条件 |
|------|------|------|
| `draft` | 刚注册，元数据填好 | seed 数据存在 |
| `testing` | 有 router + demo | router.py 存在 |
| `active` | 读→试→验→评→拿 全通过 | verify PASS + eval JSON 存在 |
| `published` | 正式发布 | 人工确认 |
| `archived` | 归档 | 手动操作 |

## CMS Schema 约束

Status 字段允许的值: `draft`, `testing`, `active`, `published`, `migrated`, `archived`

> ⚠️ **重要**: 修改 schema 后需要重启 Payload dev server 才生效。
> Schema 文件: `payload/src/collections/Modules.ts`

## 与工作流的集成

Phase 6 (模块上架) 的"评"步骤完成后，调用:

```bash
cd outputs/06_module_market/python
python ../../skills/payload-data-manager/scripts/payload_api.py update-status <slug> active
```

或在 Python 中:

```python
from payload_data_manager import PayloadClient
client = PayloadClient()
client.update_module_status("promptfoo", "active")
```
