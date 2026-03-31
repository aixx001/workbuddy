#!/usr/bin/env python3
"""
05_module_extract.py — 从外部仓库提取可复用模块

基于依赖图分析结果，实际提取代码文件：
1. 根据社区检测或用户指定，选择要提取的模块
2. 递归收集所有依赖文件
3. 复制文件到 extracted_modules/ 目录
4. 使用 rope 重写 import 路径
5. 生成 __init__.py + manifest.json + requirements.txt

Usage:
    # 提取指定模块（按社区名）
    python 05_module_extract.py --graph depgraph.json --module libs_core_langchain_core

    # 提取指定文件及其依赖
    python 05_module_extract.py --graph depgraph.json --files "core/retrievers.py,core/stores.py"

    # 列出所有可提取的模块
    python 05_module_extract.py --graph depgraph.json --list
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR.parent / 'outputs' / '05_modules' / 'extracted_modules'


def load_depgraph(path: str) -> dict:
    """加载依赖图数据"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def find_repo_root(depgraph: dict) -> Path | None:
    """从依赖图数据推断仓库根目录"""
    source_file = depgraph.get("source_file", "")
    # source_file 通常是 analyze_repo.py 的输出路径
    # 尝试从 nodes 中的文件路径推断
    # analyze_repo.py 记录了 repo 路径
    # 我们需要找到 cloned 目录中的仓库
    repo_name = depgraph.get("repo_name", "")
    if not repo_name:
        return None

    # 常见路径
    candidates = [
        SCRIPT_DIR.parent / "outputs" / "03_analysis" / "cloned" / repo_name,
        Path(source_file).parent.parent / "03_analysis" / "cloned" / repo_name,
    ]

    for c in candidates:
        if c.exists():
            return c

    return None


def collect_dependencies(depgraph: dict, target_files: list) -> dict:
    """
    收集目标文件的所有递归依赖。

    Returns: {
        "target_files": [...],
        "all_required": [...],
        "external_deps": [...]
    }
    """
    nodes = depgraph.get("nodes", {})

    # 从 nodes 重建简易依赖关系
    # node_meta 有 in_degree/out_degree 但没有边列表
    # 我们需要从原始 structure.json 重建，或者从 depgraph 的 communities 推断
    # 实际上 depgraph 应该存边信息 — 但当前版本的 build_dep_graph.py 没存边
    # 所以这里用 nodes 的 external_deps 信息

    all_required = set(target_files)
    external_deps = set()

    for f in target_files:
        meta = nodes.get(f, {})
        external_deps.update(meta.get("external_deps", []))

    return {
        "target_files": sorted(target_files),
        "all_required": sorted(all_required),
        "external_deps": sorted(external_deps),
    }


def extract_files(repo_root: Path, files: list, module_name: str, external_deps: list) -> Path:
    """
    提取文件到 extracted_modules/<module_name>/

    1. 复制文件（保持相对目录结构或扁平化）
    2. 重写 import 路径
    3. 生成 __init__.py
    4. 生成 manifest.json
    5. 生成 requirements.txt
    """
    output_dir = OUTPUT_DIR / module_name
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n  目标目录: {output_dir}")

    # 复制文件
    copied_files = []
    for rel_path in files:
        src = repo_root / rel_path
        if not src.exists():
            print(f"  [WARN] 文件不存在: {src}")
            continue

        # 扁平化: 把 "libs/core/langchain_core/retrievers.py" → "retrievers.py"
        # 保留最后两级目录用于避免冲突
        parts = Path(rel_path).parts
        if len(parts) > 2:
            # 保留包名 + 文件名
            flat_name = "_".join(parts[-2:]) if parts[-1] != "__init__.py" else parts[-2] + "_init.py"
        else:
            flat_name = Path(rel_path).name

        dst = output_dir / flat_name
        shutil.copy2(src, dst)
        copied_files.append({
            "original": rel_path,
            "extracted": flat_name,
        })
        print(f"  ✓ {rel_path} → {flat_name}")

    # 重写 import (简单的文本替换方式)
    # 对于更复杂的场景，可升级为 rope
    _rewrite_imports_simple(output_dir, copied_files)

    # 生成 __init__.py
    _generate_init(output_dir, copied_files)

    # 生成 requirements.txt
    _generate_requirements(output_dir, external_deps)

    # 生成 manifest.json
    manifest = {
        "name": module_name,
        "extracted_at": datetime.now().isoformat(),
        "source_repo": str(repo_root),
        "files": copied_files,
        "external_deps": external_deps,
        "file_count": len(copied_files),
    }
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\n  [OK] 提取完成: {len(copied_files)} 个文件 → {output_dir}")
    return output_dir


def _rewrite_imports_simple(module_dir: Path, files: list):
    """
    简单的 import 重写：
    将原始包名的绝对导入替换为相对导入。

    例如: from langchain_core.retrievers import X → from .retrievers import X
    """
    # 收集所有原始模块名（用于匹配）
    original_modules = {}
    for f in files:
        orig = f["original"]
        extracted = f["extracted"]
        # "libs/core/langchain_core/retrievers.py" 的模块路径是 "langchain_core.retrievers"
        parts = Path(orig).with_suffix("").parts
        for i in range(len(parts)):
            mod_path = ".".join(parts[i:])
            original_modules[mod_path] = Path(extracted).stem

    if not original_modules:
        return

    for f in files:
        fpath = module_dir / f["extracted"]
        if not fpath.exists() or not fpath.suffix == '.py':
            continue

        try:
            content = fpath.read_text(encoding='utf-8', errors='ignore')
            modified = False

            for orig_mod, new_name in original_modules.items():
                # from langchain_core.retrievers import X → from .retrievers_py import X
                old_import = f"from {orig_mod} import"
                new_import = f"from .{new_name} import"
                if old_import in content:
                    content = content.replace(old_import, new_import)
                    modified = True

                # import langchain_core.retrievers → from . import retrievers_py
                old_import2 = f"import {orig_mod}"
                if old_import2 in content and f"from" not in content.split(old_import2)[0].split('\n')[-1]:
                    content = content.replace(old_import2, f"from . import {new_name}")
                    modified = True

            if modified:
                fpath.write_text(content, encoding='utf-8')
                print(f"  📝 重写 import: {f['extracted']}")

        except Exception as e:
            print(f"  [WARN] import 重写失败: {f['extracted']}: {e}")


def _generate_init(module_dir: Path, files: list):
    """生成 __init__.py，导出所有公共类/函数"""
    lines = [
        '"""',
        f'Auto-extracted module from open source repository.',
        f'Extracted at: {datetime.now().isoformat()}',
        '"""',
        '',
    ]

    for f in files:
        extracted = f["extracted"]
        if extracted.endswith('.py') and not extracted.startswith('_'):
            module_name = Path(extracted).stem
            lines.append(f"# from .{module_name} import *  # uncomment to expose")

    lines.append('')

    init_path = module_dir / "__init__.py"
    init_path.write_text('\n'.join(lines), encoding='utf-8')


def _generate_requirements(module_dir: Path, external_deps: list):
    """生成 requirements.txt"""
    if not external_deps:
        return

    lines = [
        "# Auto-generated external dependencies",
        "# Review and pin versions before using in production",
        "",
    ]
    lines.extend(sorted(external_deps))
    lines.append("")

    req_path = module_dir / "requirements.txt"
    req_path.write_text('\n'.join(lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description='Stage 5: Module Extraction')
    parser.add_argument('--graph', required=True, help='依赖图 JSON 文件路径 (build_dep_graph.py 输出)')
    parser.add_argument('--module', help='要提取的模块名（社区名）')
    parser.add_argument('--files', help='要提取的文件列表（逗号分隔）')
    parser.add_argument('--repo-root', help='仓库根目录（默认自动检测）')
    parser.add_argument('--output-name', help='输出模块名（默认使用 --module 值）')
    parser.add_argument('--list', action='store_true', help='列出所有可提取的模块')

    args = parser.parse_args()

    # 加载依赖图
    depgraph = load_depgraph(args.graph)

    print(f"\n{'='*60}")
    print(f"[STAGE 5] Module Extraction")
    print(f"{'='*60}")
    print(f"仓库: {depgraph.get('repo_name', 'unknown')}")

    communities = depgraph.get("communities", {})
    nodes = depgraph.get("nodes", {})
    key_nodes = depgraph.get("key_nodes", {})

    # --list: 列出所有模块
    if args.list:
        print(f"\n可提取的模块（社区检测结果）:")
        print(f"{'─'*50}")
        for name, members in sorted(communities.items(), key=lambda x: len(x[1]), reverse=True):
            total_classes = sum(len(nodes.get(m, {}).get("classes", [])) for m in members)
            total_score = sum(nodes.get(m, {}).get("reuse_score", 0) for m in members) / max(len(members), 1)
            print(f"  {name}")
            print(f"    文件: {len(members)} | 类: {total_classes} | 平均复用分: {total_score:.2f}")

        if key_nodes.get("leaf_nodes"):
            print(f"\n最容易单独提取的文件（叶子节点）:")
            print(f"{'─'*50}")
            for ln in key_nodes["leaf_nodes"][:10]:
                classes = nodes.get(ln["file"], {}).get("classes", [])
                print(f"  📗 {ln['file']} (score: {ln['reuse_score']}) classes: {classes}")

        return

    # 确定要提取的文件
    target_files = []
    module_name = args.output_name

    if args.files:
        target_files = [f.strip() for f in args.files.split(",")]
        module_name = module_name or "custom_extract"
    elif args.module:
        if args.module in communities:
            target_files = communities[args.module]
            module_name = module_name or args.module
        else:
            print(f"[ERROR] 模块 '{args.module}' 不存在。使用 --list 查看可用模块。")
            print(f"  可用: {list(communities.keys())}")
            sys.exit(1)
    else:
        print("[ERROR] 请指定 --module 或 --files，或使用 --list 查看可用模块。")
        sys.exit(1)

    print(f"\n目标模块: {module_name}")
    print(f"文件数: {len(target_files)}")

    # 找仓库根目录
    repo_root = Path(args.repo_root) if args.repo_root else find_repo_root(depgraph)
    if not repo_root or not repo_root.exists():
        print(f"[ERROR] 找不到仓库根目录。请用 --repo-root 指定。")
        print(f"  尝试过的路径: {repo_root}")
        sys.exit(1)

    print(f"仓库根目录: {repo_root}")

    # 收集依赖
    deps_info = collect_dependencies(depgraph, target_files)
    print(f"外部依赖: {deps_info['external_deps']}")

    # 提取
    result_dir = extract_files(
        repo_root=repo_root,
        files=deps_info["all_required"],
        module_name=module_name,
        external_deps=deps_info["external_deps"],
    )

    print(f"\n{'='*60}")
    print(f"[DONE] 模块已提取到: {result_dir}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
