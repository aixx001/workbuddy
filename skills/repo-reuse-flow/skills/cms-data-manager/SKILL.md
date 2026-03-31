---
name: cms-data-manager
description: |
  Manage Payload CMS data for Module Market: seed initial data, update module records,
  sync demoPayload changes, and migrate schema updates.
  Uses Payload REST API (localhost:3000) and seed-modules.ts for data definitions.
  Triggers: seed数据, CMS更新, 模块数据, payload更新, demo数据, 重新seed
description_zh: "管理 Module Market 的 CMS 数据（seed/更新/迁移）"
description_en: "Manage Module Market CMS data (seed/update/migrate)"
---

# CMS Data Manager

> **核心问题**: 如何可靠地初始化和更新 Module Market 的 CMS 数据？

## 数据流

```
seed-modules.ts (数据定义)
       │
       ├─ pnpm seed → Payload CMS DB (SQLite/Postgres)
       │                    │
       │                    └─ REST API (localhost:3000/api/modules)
       │                            │
       └─ page.tsx ← fetch ─────────┘
```

## 操作

### 1. 首次 Seed（初始化）

在 Payload CMS 首次启动后填充模块数据：

```bash
cd outputs/06_module_market/payload
npx tsx src/seed/seed-modules.ts
```

**数据源**: `src/seed/seed-modules.ts` — 所有模块的定义（name, slug, demoEndpoint, demoPayload 等）

### 2. 更新单个模块字段

通过 Payload REST API 更新特定模块：

```bash
# 查询模块 ID
$resp = Invoke-RestMethod -Uri 'http://localhost:3000/api/modules?where[slug][equals]=ragas-evaluation'
$id = $resp.docs[0].id

# 更新字段
$body = @{
  demoPayload = @{
    question = '新问题'
    answer = '新回答'
    contexts = @('新上下文')
    reference = '新参考'
  }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Uri "http://localhost:3000/api/modules/$id" `
  -Method PATCH -Body $body -ContentType 'application/json'
```

### 3. 完整重新 Seed（覆盖）

当 `seed-modules.ts` 有大量改动时：

```bash
cd outputs/06_module_market/payload

# 方式 A: 通过 seed 脚本（会检查 slug 去重）
npx tsx src/seed/seed-modules.ts

# 方式 B: 清空重建（开发环境）
# 删除 SQLite 文件重新启动
Remove-Item database.sqlite -ErrorAction SilentlyContinue
pnpm dev  # 自动重建表
npx tsx src/seed/seed-modules.ts
```

### 4. 验证数据

```bash
# 检查模块数据
Invoke-RestMethod 'http://localhost:3000/api/modules?limit=100' | ConvertTo-Json -Depth 3

# 检查特定模块的 demoPayload
$m = Invoke-RestMethod 'http://localhost:3000/api/modules?where[slug][equals]=ragas-evaluation'
$m.docs[0].demoPayload | ConvertTo-Json
```

## 注意事项

- **Seed 幂等性**: seed 脚本通过 `slug` 判断是否已存在，已存在则跳过或更新
- **前端读取路径**: page.tsx 通过 `selectedModule.demoPayload` 读取默认值
- **端口**: Payload CMS 默认 3000，Python API 默认 8100

## 相关文件

| 文件 | 作用 |
|------|------|
| `payload/src/seed/seed-modules.ts` | 模块数据定义（唯一真相来源） |
| `payload/src/collections/Modules.ts` | CMS 表结构定义 |
| `payload/src/app/(frontend)/page.tsx` | 前端消费 CMS 数据 |
