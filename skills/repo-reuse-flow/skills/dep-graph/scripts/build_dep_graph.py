#!/usr/bin/env python3
"""
build_dep_graph.py — 从 AST 分析数据构建依赖图 + 自动检测模块边界

核心脚本：将 analyze_repo.py 的输出（*_structure.json）转化为：
1. 文件级依赖图（谁 import 谁）
2. 每个文件的复用性评分
3. 社区检测自动发现的模块边界
4. 最容易提取的叶子节点列表

Usage:
    python build_dep_graph.py <structure.json> [--output depgraph.json] [--visualize]

输入: analyze_repo.py 的输出 JSON（包含 analysis.imports + analysis.by_file）
输出: *_depgraph.json
"""

import json
import sys
import os
import argparse
import math
from pathlib import Path
from collections import defaultdict

try:
    import networkx as nx
    from networkx.algorithms import community as nx_community
except ImportError:
    print("[ERROR] networkx 未安装。运行: uv pip install --python .venv networkx")
    sys.exit(1)

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


# ============================================================================
# 从 AST 数据解析 import 关系
# ============================================================================

def _normalize_path(p: str) -> str:
    """统一路径分隔符为 /"""
    return p.replace("\\", "/")


def _guess_internal_module(import_name: str, all_files: set, repo_packages: set) -> str | None:
    """
    尝试将 import 名称映射到项目内部文件。

    例如:
      import_name = "langchain_core.retrievers"
      all_files 中有 "libs/core/langchain_core/retrievers.py"
      → 返回 "libs/core/langchain_core/retrievers.py"
    """
    # 去掉 "from X import *" 格式
    if import_name.startswith("from "):
        parts = import_name.split()
        if len(parts) >= 2:
            import_name = parts[1]

    # 策略1: 直接按模块路径匹配
    # "langchain_core.retrievers" → "langchain_core/retrievers.py"
    candidate = import_name.replace(".", "/") + ".py"
    for f in all_files:
        if f.endswith(candidate):
            return f

    # 策略2: 取最后两段匹配
    # "langchain_core.callbacks.base" → "callbacks/base.py"
    parts = import_name.split(".")
    if len(parts) >= 2:
        candidate2 = "/".join(parts[-2:]) + ".py"
        for f in all_files:
            if f.endswith(candidate2):
                return f

    # 策略3: 最后一段 + __init__.py（包导入）
    if len(parts) >= 1:
        candidate3 = parts[-1] + "/__init__.py"
        for f in all_files:
            if f.endswith(candidate3):
                return f

    # 策略4: 包名前缀匹配
    top_module = parts[0] if parts else ""
    if top_module in repo_packages:
        # 这是内部 import 但找不到具体文件（可能被截断了）
        return None

    return None


def build_graph_from_ast(data: dict) -> tuple:
    """
    从 analyze_repo.py 的输出构建依赖图。

    Returns:
        (nx.DiGraph, dict_of_node_metadata, set_of_external_deps)
    """
    analysis = data.get("analysis", {})
    imports = analysis.get("imports", [])
    by_file = analysis.get("by_file", {})
    classes_list = analysis.get("classes", [])
    functions_list = analysis.get("functions", [])

    # 收集所有已知的项目内文件
    all_files = set()
    for imp in imports:
        f = _normalize_path(imp.get("file", ""))
        if f:
            all_files.add(f)
    for f in by_file:
        all_files.add(_normalize_path(f))
    for cls in classes_list:
        f = _normalize_path(cls.get("file", ""))
        if f:
            all_files.add(f)

    # 推断项目顶层包名
    repo_packages = set()
    for f in all_files:
        parts = f.split("/")
        # 找 __init__.py 所在的包
        for i, part in enumerate(parts):
            if part == "__init__.py" and i > 0:
                repo_packages.add(parts[i - 1])
        # 也把第一层目录名加入
        if len(parts) >= 2:
            repo_packages.add(parts[0])

    print(f"  项目内文件: {len(all_files)}")
    print(f"  推断的包名: {repo_packages}")

    # 构建文件级别的类/函数索引
    file_classes = defaultdict(list)
    file_functions = defaultdict(list)
    for cls in classes_list:
        f = _normalize_path(cls.get("file", ""))
        file_classes[f].append(cls.get("name", ""))
    for func in functions_list:
        f = _normalize_path(func.get("file", ""))
        file_functions[f].append(func.get("name", ""))

    # 构建图
    G = nx.DiGraph()
    external_deps = defaultdict(set)  # file → {external deps}
    edge_labels = defaultdict(list)   # (src, dst) → [import names]

    # 添加所有文件为节点
    for f in all_files:
        G.add_node(f)

    # 从 imports 构建边
    internal_resolved = 0
    external_count = 0
    skipped_stdlib = 0

    # 标准库模块（跳过）
    stdlib_modules = {
        "os", "sys", "json", "time", "ast", "re", "math", "typing",
        "collections", "functools", "itertools", "pathlib", "abc",
        "dataclasses", "enum", "copy", "io", "logging", "warnings",
        "hashlib", "uuid", "datetime", "inspect", "traceback",
        "contextlib", "textwrap", "operator", "threading",
        "concurrent", "asyncio", "unittest", "importlib",
        "__future__", "string", "struct", "base64", "urllib",
        "http", "socket", "ssl", "email", "html", "xml",
        "types", "weakref", "pickle", "tempfile", "shutil",
        "glob", "fnmatch", "stat", "fileinput", "codecs",
        "pprint", "reprlib", "numbers", "decimal", "fractions",
        "random", "statistics", "secrets", "os.path",
        "posixpath", "ntpath", "linecache", "tokenize",
        "keyword", "token", "pdb", "profile", "timeit",
        "argparse", "getopt", "configparser", "tomllib",
        "csv", "sqlite3", "gzip", "bz2", "zipfile", "tarfile",
        "multiprocessing", "subprocess", "signal", "mmap",
        "ctypes", "array", "queue", "heapq", "bisect",
        "graphlib", "atexit", "sched",
    }

    for imp in imports:
        src_file = _normalize_path(imp.get("file", ""))
        import_name = imp.get("name", "")
        # 关键修复: 优先用 module 字段（包含实际模块路径）
        #   name = "langchain_core.caches.BaseCache" (符号名)
        #   module = "langchain_core.caches"          (模块路径) ← 用这个匹配文件
        module_path = imp.get("module", "")

        if not src_file or (not import_name and not module_path):
            continue

        # 决定用哪个做匹配
        # 优先级: module > name（对 import_from 类型）
        resolve_candidates = []
        if module_path:
            resolve_candidates.append(module_path)
        if import_name and import_name != module_path:
            resolve_candidates.append(import_name)

        # 提取顶层模块名用于 stdlib 检查
        check_name = module_path or import_name
        top_module = check_name.split(".")[0]
        if top_module in stdlib_modules:
            skipped_stdlib += 1
            continue

        # 尝试解析为内部文件（按候选列表依次尝试）
        target = None
        for candidate in resolve_candidates:
            target = _guess_internal_module(candidate, all_files, repo_packages)
            if target:
                break

        if target and target != src_file:
            G.add_edge(src_file, target)
            edge_labels[(src_file, target)].append(check_name)
            internal_resolved += 1
        elif target is None and top_module not in repo_packages:
            # 真正的外部依赖
            external_deps[src_file].add(top_module)
            external_count += 1

    print(f"  内部依赖边: {internal_resolved}")
    print(f"  外部依赖数: {external_count}")
    print(f"  图节点数: {G.number_of_nodes()}, 图边数: {G.number_of_edges()}")

    # 构建节点元数据
    node_meta = {}
    for node in G.nodes():
        in_deg = G.in_degree(node)
        out_deg = G.out_degree(node)

        # 复用性评分: 被越多文件依赖 + 自身依赖越少 = 越容易复用
        # reuse_score = in_degree / (out_degree + 1)，归一化到 0~1
        raw_score = in_deg / (out_deg + 1)
        reuse_score = round(1 - math.exp(-raw_score), 3)

        node_meta[node] = {
            "in_degree": in_deg,
            "out_degree": out_deg,
            "classes": file_classes.get(node, []),
            "functions": file_functions.get(node, []),
            "external_deps": sorted(external_deps.get(node, set())),
            "reuse_score": reuse_score,
        }

    return G, node_meta, external_deps


# ============================================================================
# 社区检测 — 自动发现模块边界
# ============================================================================

def detect_communities(G: nx.DiGraph) -> dict:
    """
    使用 Louvain 算法检测社区（模块边界）。
    NetworkX 的社区检测需要无向图，所以先转换。
    """
    if G.number_of_nodes() == 0:
        return {}

    # 转无向图用于社区检测
    G_undirected = G.to_undirected()

    # 移除孤立节点（没有任何 import 关系的文件）
    isolates = list(nx.isolates(G_undirected))
    G_for_community = G_undirected.copy()
    G_for_community.remove_nodes_from(isolates)

    if G_for_community.number_of_nodes() == 0:
        return {"isolated": isolates}

    # Louvain 社区检测
    try:
        partition = nx_community.louvain_communities(G_for_community, seed=42)
        communities = {}
        for i, comm in enumerate(partition):
            # 用社区中最常见的目录前缀命名
            paths = [f.rsplit("/", 1)[0] if "/" in f else "" for f in comm]
            prefix_counts = defaultdict(int)
            for p in paths:
                prefix_counts[p] += 1
            common_prefix = max(prefix_counts, key=prefix_counts.get) if prefix_counts else f"cluster_{i}"
            label = common_prefix.replace("/", "_") if common_prefix else f"cluster_{i}"

            communities[label] = sorted(comm)

        if isolates:
            communities["_isolated"] = sorted(isolates)

        return communities

    except Exception as e:
        print(f"  [WARN] 社区检测失败: {e}，回退到目录分组")
        # 回退: 按目录分组
        dir_groups = defaultdict(list)
        for node in G.nodes():
            dir_name = node.rsplit("/", 1)[0] if "/" in node else "_root"
            dir_groups[dir_name].append(node)
        return dict(dir_groups)


# ============================================================================
# 提取关键节点
# ============================================================================

def find_key_nodes(G: nx.DiGraph, node_meta: dict) -> dict:
    """找出叶子节点（最容易提取）和枢纽节点（核心依赖）"""
    leaf_nodes = []  # 被别人依赖但自己不依赖内部文件
    hub_nodes = []   # 被大量文件依赖的核心

    for node, meta in node_meta.items():
        if meta["in_degree"] > 0 and meta["out_degree"] == 0:
            leaf_nodes.append((node, meta["reuse_score"]))
        if meta["in_degree"] >= 5:
            hub_nodes.append((node, meta["in_degree"]))

    leaf_nodes.sort(key=lambda x: x[1], reverse=True)
    hub_nodes.sort(key=lambda x: x[1], reverse=True)

    return {
        "leaf_nodes": [{"file": n, "reuse_score": s} for n, s in leaf_nodes[:20]],
        "hub_nodes": [{"file": n, "dependents": d} for n, d in hub_nodes[:20]],
    }


def compute_extraction_cost(G: nx.DiGraph, target_files: list) -> dict:
    """计算提取一组文件需要带上的所有依赖"""
    required = set(target_files)
    queue = list(target_files)

    while queue:
        current = queue.pop(0)
        for _, dep in G.out_edges(current):
            if dep not in required:
                required.add(dep)
                queue.append(dep)

    return {
        "target_files": sorted(target_files),
        "total_required": sorted(required),
        "additional_deps": sorted(required - set(target_files)),
        "file_count": len(required),
    }


# ============================================================================
# 主函数
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="从 AST 分析数据构建依赖图 + 自动检测模块边界"
    )
    parser.add_argument("input", help="analyze_repo.py 输出的 JSON 文件")
    parser.add_argument("--output", "-o", help="输出文件路径（默认: 输入文件名_depgraph.json）")
    parser.add_argument("--extract-cost", help="计算提取某个文件的成本（逗号分隔的文件列表）")

    args = parser.parse_args()

    # 加载 AST 数据
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[ERROR] 文件不存在: {input_path}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"[DEP GRAPH] 构建依赖图")
    print(f"{'='*60}")
    print(f"输入: {input_path}")

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    repo_name = data.get("repo_name", input_path.stem)
    print(f"仓库: {repo_name}")

    # 1. 构建依赖图
    print(f"\n[1/3] 构建依赖图...")
    G, node_meta, external_deps = build_graph_from_ast(data)

    # 2. 社区检测
    print(f"\n[2/3] 社区检测（Louvain）...")
    communities = detect_communities(G)
    print(f"  检测到 {len(communities)} 个模块簇:")
    for name, members in sorted(communities.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"    {name}: {len(members)} 个文件")

    # 3. 关键节点
    print(f"\n[3/3] 分析关键节点...")
    key_nodes = find_key_nodes(G, node_meta)
    print(f"  叶子节点（最容易提取）: {len(key_nodes['leaf_nodes'])} 个")
    if key_nodes["leaf_nodes"]:
        for ln in key_nodes["leaf_nodes"][:5]:
            print(f"    📗 {ln['file']} (score: {ln['reuse_score']})")
    print(f"  枢纽节点（核心依赖）: {len(key_nodes['hub_nodes'])} 个")
    if key_nodes["hub_nodes"]:
        for hn in key_nodes["hub_nodes"][:5]:
            print(f"    📕 {hn['file']} (被 {hn['dependents']} 个文件依赖)")

    # 提取成本计算
    extraction_cost = None
    if args.extract_cost:
        target_files = [f.strip() for f in args.extract_cost.split(",")]
        print(f"\n[COST] 计算提取成本: {target_files}")
        extraction_cost = compute_extraction_cost(G, target_files)
        print(f"  目标文件: {len(target_files)}")
        print(f"  总共需要: {extraction_cost['file_count']} 个文件")
        print(f"  额外依赖: {len(extraction_cost['additional_deps'])} 个")

    # 输出
    output_path = args.output or str(input_path).replace("_structure.json", "_depgraph.json").replace(".json", "_depgraph.json")
    if output_path == str(input_path):
        output_path = str(input_path).replace(".json", "_depgraph.json")

    result = {
        "repo_name": repo_name,
        "source_file": str(input_path),
        "graph_stats": {
            "nodes": G.number_of_nodes(),
            "edges": G.number_of_edges(),
            "connected_components": nx.number_weakly_connected_components(G),
        },
        "nodes": node_meta,
        "communities": communities,
        "key_nodes": key_nodes,
        "all_external_deps": sorted(set(
            dep for deps in external_deps.values() for dep in deps
        )),
    }
    if extraction_cost:
        result["extraction_cost"] = extraction_cost

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n[SAVED] {output_path}")
    print(f"[DONE] 依赖图构建完成")

    return result


if __name__ == "__main__":
    main()
