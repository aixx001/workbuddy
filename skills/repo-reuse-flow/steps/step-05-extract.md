# Step 5: 模块提取 (extract)

**触发条件**: 无已提取或已安装的模块

**加载 Skill**: `skills/module-extractor`

## 执行步骤

### 决策：安装型 vs 提取型

```bash
# 先预览，看会拉进多少文件
.venv\Scripts\python.exe scripts/extract_feature_module.py \
  --repo outputs/03_analysis/cloned/<repo>/src/<package> \
  --entry <target_module> \
  --name <module_name> --preview
```

- 拉进 >50% 文件 → **安装型**（pip install + 薄壳 API）
- 拉进 <50% 文件 → **提取型**（代码复制 + import 重写）

### 安装型操作

1. `pip install <package>`
2. 创建 `outputs/06_module_market/python/modules/<project>/<feature>/`
3. 编写 `router.py`（100% 调用源库 API）
4. 编写 `meta.json`（溯源信息）

### 提取型操作

1. 去掉 `--preview`，实际提取
2. 检查 `outputs/05_modules/extracted_modules/<module>/`
3. 验证 `manifest.json` 和 `requirements.txt`

## 完成检查

- [ ] 模块目录存在（`05_modules/` 或 `06_module_market/python/modules/`）
- [ ] 有 `meta.json` 或 `manifest.json` 记录溯源
