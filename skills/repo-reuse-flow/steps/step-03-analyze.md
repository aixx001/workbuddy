# Step 3: 仓库分析 (analyze)

**触发条件**: `outputs/03_analysis/structures/` 下无 JSON 文件

**加载 Skill**: `skills/repo-analyzer`

## 执行步骤

1. **克隆候选仓库**
   ```bash
   scripts/clone_repos.ps1 -Repos "owner/repo1","owner/repo2"
   ```

2. **优先读取 AI 指令文件**
   - 检查每个克隆仓库中的 `AGENTS.md`、`CLAUDE.md`、`CONTRIBUTING.md`
   - 这些文件由维护者编写，信号密度最高

3. **运行 AST 结构分析**
   ```bash
   .venv\Scripts\python.exe scripts/analyze_repo.py \
     outputs/03_analysis/cloned/<repo> \
     -o outputs/03_analysis/structures/<repo>_structure.json
   ```

4. **可选：生成 gitingest 摘要**
   ```bash
   scripts/gitingest_all.ps1
   ```

## 完成检查

- [ ] `outputs/03_analysis/structures/*.json` 至少有一个文件
- [ ] `outputs/03_analysis/cloned/` 有克隆的仓库源码
