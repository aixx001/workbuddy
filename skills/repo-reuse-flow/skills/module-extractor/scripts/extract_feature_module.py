#!/usr/bin/env python3
"""
extract_feature_module.py — 需求驱动的功能模块提取

与 05_module_extract.py (Louvain 社区检测) 不同，这个脚本：
1. 从用户指定的功能目录出发 (如 src/ragas/metrics/)
2. 递归追踪所有内部 import，构建完整依赖子图
3. 只提取这个子图中的文件
4. 重写 import 路径为相对导入
5. 验证 import 完整性
6. 生成 README + manifest

Usage:
    # 提取 ragas 的评估模块
    python extract_feature_module.py \
        --repo outputs/03_analysis/cloned/ragas/src/ragas \
        --entry metrics evaluation.py \
        --name evaluation \
        --desc "RAG evaluation metrics: faithfulness, relevance, correctness"

    # 提取 ragas 的 prompt 模块
    python extract_feature_module.py \
        --repo outputs/03_analysis/cloned/ragas/src/ragas \
        --entry prompt \
        --name prompt_management \
        --desc "Structured prompt templates with Pydantic models"

    # 提取 ragas 的 testset 模块（题目生成）
    python extract_feature_module.py \
        --repo outputs/03_analysis/cloned/ragas/src/ragas \
        --entry testset \
        --name question_synthesis \
        --desc "Automatic test question generation from documents"

    # 预览模式（不实际提取，只显示文件列表）
    python extract_feature_module.py \
        --repo outputs/03_analysis/cloned/ragas/src/ragas \
        --entry metrics evaluation.py \
        --name evaluation --preview
"""

import argparse
import ast
import json
import os
import re
import shutil
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR.parent / 'outputs' / '05_modules' / 'extracted_modules'


# ============================================================================
# Import 追踪 — 从入口文件递归收集所有内部依赖
# ============================================================================

def parse_imports(file_path: Path) -> list[dict]:
    """用 AST 精确解析文件的 import 语句"""
    try:
        source = file_path.read_text(encoding='utf-8', errors='replace')
        tree = ast.parse(source, filename=str(file_path))
    except (SyntaxError, Exception):
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({
                    "type": "import",
                    "module": alias.name,
                    "name": None,
                    "level": 0,
                })
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            level = node.level or 0
            for alias in node.names:
                imports.append({
                    "type": "import_from",
                    "module": module,
                    "name": alias.name,
                    "level": level,
                })
    return imports


def resolve_import_to_file(
    import_info: dict,
    current_file: Path,
    repo_root: Path,
    pkg_root: Path,
) -> Path | None:
    """
    将 import 语句解析为具体文件路径。

    支持：
    - 相对导入: from .base import X  (level > 0)
    - 绝对导入: from ragas.metrics import X (level == 0, 解析为内部)
    """
    module = import_info["module"]
    level = import_info["level"]

    if level > 0:
        # 相对导入
        base_dir = current_file.parent
        for _ in range(level - 1):
            base_dir = base_dir.parent

        if module:
            parts = module.split(".")
            target = base_dir / "/".join(parts)
        else:
            # from . import X  →  X 可能是同目录的模块
            name = import_info.get("name", "")
            if name:
                target = base_dir / name
            else:
                return None
    else:
        # 绝对导入 — 尝试在 repo_root 或 pkg_root 下解析
        if not module:
            return None

        parts = module.split(".")

        # 尝试多种解析路径
        candidates = []

        # 1. 从 repo_root 解析 (如 ragas.metrics.base)
        candidates.append(repo_root / "/".join(parts))

        # 2. 从 pkg_root 的父目录解析
        if pkg_root != repo_root:
            candidates.append(pkg_root.parent / "/".join(parts))

        # 3. 直接从 pkg_root 解析 (去掉包前缀)
        # 如果 pkg_root 是 ragas/, module 是 ragas.metrics.base → metrics/base
        pkg_name = pkg_root.name
        if parts[0] == pkg_name:
            candidates.append(pkg_root / "/".join(parts[1:]))

        for target in candidates:
            # 尝试 target.py 或 target/__init__.py
            if target.with_suffix(".py").exists():
                return target.with_suffix(".py")
            if (target / "__init__.py").exists():
                return target / "__init__.py"

        return None

    # 尝试 target.py 或 target/__init__.py
    if target.with_suffix(".py").exists():
        return target.with_suffix(".py")
    if (target / "__init__.py").exists():
        return target / "__init__.py"

    return None


def trace_imports_recursive(
    entry_files: list[Path],
    repo_root: Path,
    pkg_root: Path,
    max_depth: int = 20,
) -> dict:
    """
    从入口文件递归追踪所有内部 import。

    Returns:
        {
            "internal_files": set of Path,
            "external_deps": set of str,
            "unresolved": set of str,
            "trace_log": list[str],
        }
    """
    visited = set()
    queue = list(entry_files)
    external_deps = set()
    unresolved = set()
    trace_log = []

    depth = 0
    while queue and depth < max_depth:
        depth += 1
        next_queue = []

        for file_path in queue:
            file_path = file_path.resolve()
            if file_path in visited:
                continue
            visited.add(file_path)

            imports = parse_imports(file_path)
            rel = file_path.relative_to(repo_root) if file_path.is_relative_to(repo_root) else file_path

            for imp in imports:
                resolved = resolve_import_to_file(imp, file_path, repo_root, pkg_root)

                if resolved and resolved.exists():
                    resolved = resolved.resolve()
                    if resolved not in visited:
                        next_queue.append(resolved)
                        trace_log.append(f"  {rel} → {resolved.relative_to(repo_root)}")
                else:
                    # 归类为外部依赖
                    mod = imp["module"]
                    if mod and imp["level"] == 0:
                        top_level = mod.split(".")[0]
                        # 排除标准库和已知 builtins
                        if top_level not in _STDLIB_MODULES:
                            external_deps.add(top_level)
                    elif imp["level"] > 0 and not resolved:
                        unresolved.add(f"{rel}: {_format_import(imp)}")

        queue = next_queue

    return {
        "internal_files": visited,
        "external_deps": external_deps,
        "unresolved": unresolved,
        "trace_log": trace_log,
    }


def _format_import(imp: dict) -> str:
    """格式化 import 信息用于日志"""
    dots = "." * imp.get("level", 0)
    mod = imp.get("module", "")
    name = imp.get("name", "")
    if imp["type"] == "import_from":
        return f"from {dots}{mod} import {name}"
    return f"import {mod}"


# Python 标准库模块列表（常用）
_STDLIB_MODULES = {
    "abc", "ast", "asyncio", "base64", "bisect", "builtins", "calendar", "cmath",
    "codecs", "collections", "colorsys", "concurrent", "contextlib", "contextvars",
    "copy", "csv", "ctypes", "dataclasses", "datetime", "decimal", "difflib",
    "dis", "email", "enum", "errno", "faulthandler", "fcntl", "fileinput",
    "fnmatch", "fractions", "functools", "gc", "getpass", "gettext", "glob",
    "gzip", "hashlib", "heapq", "hmac", "html", "http", "importlib", "inspect",
    "io", "ipaddress", "itertools", "json", "keyword", "linecache", "locale",
    "logging", "lzma", "math", "mimetypes", "multiprocessing", "numbers",
    "operator", "os", "pathlib", "pickle", "platform", "pprint", "profile",
    "queue", "random", "re", "resource", "secrets", "select", "shelve",
    "shlex", "shutil", "signal", "site", "socket", "sqlite3", "ssl",
    "statistics", "string", "struct", "subprocess", "sys", "sysconfig",
    "tempfile", "textwrap", "threading", "time", "timeit", "token",
    "tokenize", "traceback", "tracemalloc", "types", "typing", "typing_extensions",
    "unicodedata", "unittest", "urllib", "uuid", "venv", "warnings",
    "weakref", "xml", "xmlrpc", "zipfile", "zipimport", "zlib",
    "__future__", "_thread", "posixpath", "ntpath", "genericpath",
    "stat", "posix", "nt", "pwd", "grp", "termios", "tty",
    "pty", "pipes", "resource", "syslog", "optparse", "argparse",
    "configparser", "tomllib", "tomli",
    # Typing extensions
    "typing_extensions", "annotated_types",
}


# ============================================================================
# 文件提取 + Import 重写
# ============================================================================

def extract_module(
    internal_files: set[Path],
    repo_root: Path,
    pkg_root: Path,
    module_name: str,
    description: str,
    external_deps: set[str],
    unresolved: set[str],
) -> Path:
    """
    提取文件到 extracted_modules/<module_name>/，保留目录结构。
    """
    output_dir = OUTPUT_DIR / module_name
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 按相对于 pkg_root 的路径复制（保留目录结构）
    file_map = []  # [(original_rel, extracted_rel)]

    for file_path in sorted(internal_files):
        try:
            rel = file_path.relative_to(pkg_root)
        except ValueError:
            try:
                rel = file_path.relative_to(repo_root)
            except ValueError:
                rel = Path(file_path.name)

        dst = output_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, dst)
        file_map.append((str(rel), str(rel)))

    print(f"\n  ✅ 复制了 {len(file_map)} 个文件到 {output_dir}")

    # 重写绝对 import 为相对 import
    _rewrite_imports_structural(output_dir, pkg_root.name)

    # 确保每个目录都有 __init__.py
    _ensure_init_files(output_dir)

    # 生成 manifest
    manifest = {
        "name": module_name,
        "description": description,
        "extracted_at": datetime.now().isoformat(),
        "source_repo": str(repo_root),
        "source_package": pkg_root.name,
        "files": [{"original": o, "extracted": e} for o, e in file_map],
        "external_deps": sorted(external_deps),
        "unresolved_imports": sorted(unresolved) if unresolved else [],
        "file_count": len(file_map),
    }

    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8'
    )

    # 生成 requirements.txt
    if external_deps:
        lines = [
            "# Auto-generated external dependencies",
            "# Review and pin versions before using in production",
            "",
        ]
        lines.extend(sorted(external_deps))
        lines.append("")
        (output_dir / "requirements.txt").write_text("\n".join(lines), encoding='utf-8')

    # 生成 README
    _generate_readme(output_dir, module_name, description, file_map, external_deps, unresolved)

    return output_dir


def _rewrite_imports_structural(output_dir: Path, pkg_name: str):
    """
    重写绝对导入为相对导入。
    保留目录结构的情况下，只需要处理包名前缀。
    例如: from ragas.metrics.base import X → from .metrics.base import X (在根 __init__)
          from ragas.prompt import X → from ..prompt import X (在 metrics/ 内)
    """
    for py_file in output_dir.rglob("*.py"):
        try:
            content = py_file.read_text(encoding='utf-8', errors='replace')
            original = content

            # 计算当前文件相对于 output_dir 的深度
            rel = py_file.relative_to(output_dir)
            depth = len(rel.parts) - 1  # 文件本身不算

            # 替换 from <pkg_name>.X.Y import Z → from .X.Y import Z (调整 . 数量)
            pattern = rf'from\s+{re.escape(pkg_name)}\.(\S+)\s+import'

            def replace_import(match):
                sub_module = match.group(1)
                # 从当前文件位置计算需要多少个 .
                dots = "." * max(depth, 1)
                return f"from {dots}{sub_module} import"

            content = re.sub(pattern, replace_import, content)

            # 替换 from <pkg_name> import X → from . import X
            pattern2 = rf'from\s+{re.escape(pkg_name)}\s+import'
            dots2 = "." * max(depth, 1)
            content = re.sub(pattern2, f"from {dots2} import", content)

            # 替换 import <pkg_name>.X → from . import X
            pattern3 = rf'^import\s+{re.escape(pkg_name)}\.(\S+)'
            content = re.sub(pattern3, rf"from . import \1", content, flags=re.MULTILINE)

            if content != original:
                py_file.write_text(content, encoding='utf-8')
                print(f"  📝 重写 import: {rel}")

        except Exception as e:
            print(f"  [WARN] import 重写失败: {py_file.name}: {e}")


def _ensure_init_files(output_dir: Path):
    """确保每个 Python 包目录都有 __init__.py"""
    for dirpath in output_dir.rglob("*"):
        if dirpath.is_dir():
            init_file = dirpath / "__init__.py"
            if not init_file.exists():
                # 检查目录是否包含 .py 文件
                has_py = any(f.suffix == '.py' for f in dirpath.iterdir())
                if has_py:
                    init_file.write_text("", encoding='utf-8')


def _generate_readme(
    output_dir: Path,
    module_name: str,
    description: str,
    file_map: list,
    external_deps: set,
    unresolved: set,
):
    """生成模块 README"""
    lines = [
        f"# {module_name}",
        "",
        f"> {description}",
        "",
        f"**提取时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**文件数量**: {len(file_map)}",
        f"**外部依赖**: {', '.join(sorted(external_deps)) if external_deps else '无'}",
        "",
    ]

    if unresolved:
        lines.extend([
            "## ⚠️ 未解析的 import",
            "",
            "以下 import 可能需要手动处理：",
            "",
        ])
        for u in sorted(unresolved):
            lines.append(f"- `{u}`")
        lines.append("")

    lines.extend([
        "## 文件列表",
        "",
        "| 文件 | 说明 |",
        "|------|------|",
    ])

    for orig, extracted in file_map:
        lines.append(f"| `{extracted}` | from `{orig}` |")

    lines.extend([
        "",
        "## 使用方式",
        "",
        "```python",
        f"# 将 {module_name}/ 目录复制到你的项目中",
        f"from {module_name} import ...",
        "```",
        "",
    ])

    (output_dir / "README.md").write_text("\n".join(lines), encoding='utf-8')


# ============================================================================
# 入口文件收集
# ============================================================================

def collect_entry_files(repo_root: Path, entries: list[str]) -> list[Path]:
    """
    从 --entry 参数收集入口文件。
    entry 可以是目录 (收集其下所有 .py) 或单个文件。
    """
    files = []
    for entry in entries:
        target = repo_root / entry
        if target.is_dir():
            for py in target.rglob("*.py"):
                files.append(py)
            print(f"  📁 {entry}/ → {sum(1 for _ in target.rglob('*.py'))} 个 .py 文件")
        elif target.exists():
            files.append(target)
            print(f"  📄 {entry}")
        elif target.with_suffix(".py").exists():
            files.append(target.with_suffix(".py"))
            print(f"  📄 {entry}.py")
        else:
            print(f"  [WARN] 入口不存在: {entry}")
    return files


# ============================================================================
# main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="需求驱动的功能模块提取 — 从指定目录出发，递归追踪 import 依赖",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 提取 ragas 评估模块
  python extract_feature_module.py \\
      --repo outputs/03_analysis/cloned/ragas/src/ragas \\
      --entry metrics evaluation.py \\
      --name evaluation

  # 预览模式
  python extract_feature_module.py \\
      --repo outputs/03_analysis/cloned/ragas/src/ragas \\
      --entry metrics \\
      --name evaluation --preview
        """,
    )
    parser.add_argument("--repo", required=True, help="源仓库的包根目录 (如 ragas/src/ragas)")
    parser.add_argument("--entry", nargs="+", required=True,
                        help="入口目录或文件 (相对于 --repo)，可以多个")
    parser.add_argument("--name", required=True, help="输出模块名")
    parser.add_argument("--desc", default="", help="模块描述")
    parser.add_argument("--preview", action="store_true", help="仅预览，不实际提取")
    parser.add_argument("--max-depth", type=int, default=20, help="最大递归追踪深度")

    args = parser.parse_args()

    repo_root = Path(args.repo).resolve()
    if not repo_root.exists():
        print(f"[ERROR] 仓库路径不存在: {repo_root}")
        sys.exit(1)

    # pkg_root 就是 repo_root (如 ragas/src/ragas/ 是包的根)
    pkg_root = repo_root

    print(f"\n{'='*60}")
    print(f"[Feature Module Extraction] 需求驱动提取")
    print(f"{'='*60}")
    print(f"源仓库: {repo_root}")
    print(f"模块名: {args.name}")
    print(f"入口点:")

    # 收集入口文件
    entry_files = collect_entry_files(repo_root, args.entry)
    if not entry_files:
        print("[ERROR] 没有找到入口文件")
        sys.exit(1)

    print(f"\n共 {len(entry_files)} 个入口文件")

    # 递归追踪 import
    print(f"\n[Tracing] 递归追踪 import 依赖...")
    result = trace_imports_recursive(entry_files, repo_root, pkg_root, max_depth=args.max_depth)

    internal = result["internal_files"]
    external = result["external_deps"]
    unresolved_imports = result["unresolved"]

    print(f"\n  内部文件: {len(internal)}")
    print(f"  外部依赖: {len(external)} → {sorted(external)}")
    if unresolved_imports:
        print(f"  ⚠️ 未解析: {len(unresolved_imports)}")
        for u in sorted(unresolved_imports)[:10]:
            print(f"    - {u}")

    # 预览模式
    if args.preview:
        print(f"\n[Preview] 将提取以下文件:")
        print(f"{'─'*50}")
        for f in sorted(internal):
            try:
                rel = f.relative_to(pkg_root)
            except ValueError:
                rel = f.name
            print(f"  📄 {rel}")
        print(f"\n共 {len(internal)} 个文件")
        print(f"外部依赖: {sorted(external)}")
        return

    # 实际提取
    print(f"\n[Extracting] 提取模块到 outputs/05_modules/extracted_modules/{args.name}/")
    output_path = extract_module(
        internal_files=internal,
        repo_root=repo_root,
        pkg_root=pkg_root,
        module_name=args.name,
        description=args.desc or f"Feature module extracted from {repo_root.name}",
        external_deps=external,
        unresolved=unresolved_imports,
    )

    print(f"\n{'='*60}")
    print(f"[DONE] ✅ 模块已提取到: {output_path}")
    print(f"{'='*60}")

    # 验证报告
    print(f"\n[Validation] 提取后验证:")
    validate_extraction(output_path)


def validate_extraction(module_dir: Path):
    """验证提取后的模块 import 完整性"""
    issues = []
    py_files = list(module_dir.rglob("*.py"))

    for py_file in py_files:
        imports = parse_imports(py_file)
        for imp in imports:
            mod = imp.get("module", "")
            level = imp.get("level", 0)

            if level > 0:
                # 相对导入 — 检查目标是否存在
                target = resolve_import_to_file(imp, py_file, module_dir, module_dir)
                if not target or not target.exists():
                    rel = py_file.relative_to(module_dir)
                    issues.append(f"  ❌ {rel}: {_format_import(imp)} → 目标不存在")

    if issues:
        print(f"  发现 {len(issues)} 个潜在问题:")
        for issue in issues[:20]:
            print(issue)
    else:
        print(f"  ✅ 所有 {len(py_files)} 个文件的内部 import 验证通过")


if __name__ == '__main__':
    main()
