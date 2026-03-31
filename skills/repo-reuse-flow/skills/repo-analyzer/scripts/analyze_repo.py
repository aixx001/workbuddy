#!/usr/bin/env python3
"""
repo_analyzer.py — 仓库结构分析脚本 v2
使用 Python AST 模块分析 Python 项目，提取完整信息：
- 类：继承关系、装饰器、docstring、实例属性
- 函数：参数签名、类型注解、装饰器、返回值类型、async 标记
- 导入：完整模块路径

Usage:
    python analyze_repo.py /path/to/repo [--output output.json] [--max-files 300]
"""

import os
import sys
import json
import time
import ast
import glob
import argparse
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional


# ============================================================================
# AST 解析核心
# ============================================================================

def get_docstring(node: ast.AST) -> Optional[str]:
    """提取 docstring"""
    if (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and ast.get_docstring(node)):
        doc = ast.get_docstring(node)
        # 截断长 docstring
        if len(doc) > 300:
            doc = doc[:300] + "..."
        return doc
    return None


def get_decorators(node: ast.AST) -> list[str]:
    """提取装饰器列表"""
    return [d.attr if isinstance(d, ast.Attribute) else d.id if isinstance(d, ast.Name) else str(ast.unparse(d))
            for d in getattr(node, 'decorator_list', [])]


def get_base_classes(node: ast.ClassDef) -> list[str]:
    """提取类继承的父类"""
    bases = []
    for base in node.bases:
        if isinstance(base, ast.Name):
            bases.append(base.id)
        elif isinstance(base, ast.Attribute):
            bases.append(ast.unparse(base))
        elif isinstance(base, ast.Subscript):
            bases.append(ast.unparse(base))
        else:
            bases.append(ast.unparse(base))
    return bases


def get_type_annotation(node: ast.AST) -> Optional[str]:
    """提取类型注解"""
    if isinstance(node, ast.Name):
        return node.id
    return ast.unparse(node) if hasattr(ast, 'unparse') else None


def parse_function_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict:
    """解析函数签名"""
    sig = {
        "async": isinstance(node, ast.AsyncFunctionDef),
        "parameters": [],
        "returns": None,
        "decorators": get_decorators(node),
        "docstring": get_docstring(node),
    }

    # 返回类型
    if node.returns:
        sig["returns"] = ast.unparse(node.returns) if hasattr(ast, 'unparse') else None

    # 参数
    for arg in node.args.args:
        param = {"name": arg.arg}
        if arg.annotation:
            param["type"] = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else None
        # 默认值
        defaults = node.args.defaults
        posonly = len(node.args.posonlyargs)
        args_len = len(node.args.args)
        # 默认值从右向左对应
        idx = len(node.args.args) - len(defaults) - posonly
        if idx < len(node.args.args) and arg in node.args.args:
            try:
                def_idx = node.args.args.index(arg) - posonly - (len(node.args.args) - len(defaults))
                if def_idx >= 0 and def_idx < len(defaults):
                    param["default"] = ast.unparse(defaults[def_idx])
            except (ValueError, IndexError):
                pass
        sig["parameters"].append(param)

    # *args, **kwargs
    if node.args.vararg:
        v = {"name": f"*{node.args.vararg.arg}"}
        if node.args.vararg.annotation:
            v["type"] = ast.unparse(node.args.vararg.annotation)
        sig["parameters"].append(v)
    if node.args.kwarg:
        v = {"name": f"**{node.args.kwarg.arg}"}
        if node.args.kwarg.annotation:
            v["type"] = ast.unparse(node.args.kwarg.annotation)
        sig["parameters"].append(v)

    return sig


def parse_class_body(node: ast.ClassDef) -> dict:
    """解析类体，提取类变量和内部类"""
    class_vars = []
    nested_classes = []

    for item in node.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            # 类型注解的类变量: name: Type = value
            var = {"name": item.target.id}
            if item.annotation:
                var["type"] = ast.unparse(item.annotation) if hasattr(ast, 'unparse') else None
            if item.value:
                var["value"] = ast.unparse(item.value)
            class_vars.append(var)
        elif isinstance(item, ast.Assign):
            # 普通赋值: name = value
            for target in item.targets:
                if isinstance(target, ast.Name):
                    var = {"name": target.id}
                    if item.value:
                        var["value"] = ast.unparse(item.value)
                    class_vars.append(var)
        elif isinstance(item, ast.ClassDef):
            nested_classes.append(item.name)

    return class_vars, nested_classes


def analyze_python_file(file_path: str, repo_root: str) -> dict:
    """使用 AST 分析单个 Python 文件"""
    try:
        with open(file_path, encoding="utf-8", errors="replace") as f:
            source = f.read()
    except Exception as e:
        return {"error": str(e)}

    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError as e:
        return {"error": f"SyntaxError: {e}"}

    result = {
        "file": os.path.relpath(file_path, repo_root),
        "line_count": len(source.splitlines()),
        "classes": [],
        "functions": [],  # 模块级函数
        "imports": [],
        "nested_items": [],  # 嵌套在类中的方法
    }

    # 遍历 AST 节点
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # 跳过嵌套类（只在类体内出现）
            if node.col_offset == 0:  # 顶层类
                class_info = {
                    "name": node.name,
                    "start_line": node.lineno,
                    "end_line": node.end_lineno,
                    "bases": get_base_classes(node),
                    "decorators": get_decorators(node),
                    "docstring": get_docstring(node),
                    "class_vars": [],
                    "methods": [],
                    "nested_classes": [],
                }
                # 类体
                class_vars, nested_classes = parse_class_body(node)
                class_info["class_vars"] = class_vars
                class_info["nested_classes"] = nested_classes

                # 方法
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_sig = parse_function_signature(item)
                        class_info["methods"].append({
                            "name": item.name,
                            "start_line": item.lineno,
                            "end_line": item.end_lineno,
                            **method_sig,
                        })

                result["classes"].append(class_info)

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # 模块级函数（不在类内）
            func_sig = parse_function_signature(node)
            result["functions"].append({
                "name": node.name,
                "start_line": node.lineno,
                "end_line": node.end_lineno,
                **func_sig,
            })

        elif isinstance(node, ast.Import):
            for alias in node.names:
                imp = {
                    "name": alias.name,
                    "alias": alias.asname,
                    "start_line": node.lineno,
                    "type": "import",
                }
                if alias.name == "*":
                    result["imports"].append({**imp, "name": "from <module> import *"})
                else:
                    result["imports"].append(imp)

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                if alias.name == "*":
                    result["imports"].append({
                        "name": f"from {module} import *",
                        "alias": None,
                        "start_line": node.lineno,
                        "type": "import_from",
                    })
                else:
                    result["imports"].append({
                        "name": f"{module}.{alias.name}" if module else alias.name,
                        "alias": alias.asname,
                        "start_line": node.lineno,
                        "type": "import_from",
                        "module": module,
                    })

    return result


# ============================================================================
# 目录扫描
# ============================================================================

def quick_dir_summary(repo_path: str) -> dict:
    """快速目录结构摘要"""
    root = Path(repo_path)
    by_ext = {}
    total = 0
    skip_dirs = {".git", "venv", ".venv", "node_modules", "dist", "build",
                 "__pycache__", ".pytest_cache", ".tox", ".mypy_cache"}

    for f in root.rglob("*"):
        if f.is_file():
            parts = f.parts
            if any(d in skip_dirs for d in parts):
                continue
            total += 1
            ext = f.suffix or "(none)"
            by_ext[ext] = by_ext.get(ext, 0) + 1

    subdirs = []
    for d in root.iterdir():
        if d.is_dir() and not d.name.startswith("."):
            count = sum(1 for _ in d.rglob("*") if _.is_file())
            subdirs.append((d.name, count))
    subdirs.sort(key=lambda x: x[1], reverse=True)

    return {
        "total_files": total,
        "by_extension": dict(sorted(by_ext.items(), key=lambda x: x[1], reverse=True)[:20]),
        "largest_dirs": subdirs[:15],
        "root_files": [f.name for f in root.iterdir() if f.is_file()],
    }


def find_py_files(repo_path: str, max_files: int = 300) -> list:
    """找出核心 Python 代码文件"""
    root = Path(repo_path)
    skip_dirs = {
        "test", "tests", "__pycache__", ".git", "venv", ".venv",
        "node_modules", "dist", "build", ".tox", ".mypy_cache",
        "examples", "docs", ".idea", ".vscode",
        "coverage", ".pytest_cache", ".hypothesis",
    }

    files = []
    for f in root.rglob("*.py"):
        parts = f.parts
        # 跳过测试文件
        if any(d in parts for d in skip_dirs):
            continue
        name = f.name
        if name.startswith("test_") or name.startswith("conftest") or "_test." in name:
            continue
        files.append(str(f))
        if len(files) >= max_files:
            break

    return files


# ============================================================================
# 主分析函数
# ============================================================================

def analyze_repo(repo_path: str, max_files: int = 300, output_path: str = None) -> dict:
    """分析仓库"""
    repo = Path(repo_path).resolve()
    if not repo.exists():
        print(f"ERROR: {repo} not found")
        return {}

    t0 = time.time()
    result = {
        "repo": str(repo),
        "repo_name": repo.name,
        "analyzed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "analyzer": "python-ast-v2",
    }

    # 1. 目录扫描
    print(f"[1/3] Directory scan...")
    result["dir_summary"] = quick_dir_summary(str(repo))
    print(f"  Total files: {result['dir_summary']['total_files']}")

    # 2. 找代码文件
    print(f"[2/3] Finding Python files...")
    py_files = find_py_files(str(repo), max_files=max_files)
    print(f"  Found {len(py_files)} Python files")

    # 3. AST 分析
    if py_files:
        print(f"[3/3] AST analyzing {len(py_files)} files...")
        all_classes = []
        all_functions = []
        all_imports = []
        by_file = {}

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(analyze_python_file, fp, str(repo)): fp for fp in py_files}
            done = 0
            for future in as_completed(futures):
                done += 1
                if done % 50 == 0:
                    print(f"  Progress: {done}/{len(py_files)}")
                data = future.result()
                fp = futures[future]

                if "error" in data:
                    continue

                file_key = data["file"]

                # 按文件聚合
                file_summary = {
                    "classes": [],
                    "functions": [],
                    "imports": [],
                }

                for cls in data["classes"]:
                    class_entry = {
                        "file": file_key,
                        "name": cls["name"],
                        "start_line": cls["start_line"],
                        "end_line": cls["end_line"],
                        "bases": cls["bases"],  # 继承关系
                        "decorators": cls["decorators"],  # 装饰器
                        "docstring": cls["docstring"],
                        "class_vars": cls["class_vars"],
                        "method_count": len(cls["methods"]),
                        "methods": cls["methods"],
                        "nested_classes": cls["nested_classes"],
                    }
                    all_classes.append(class_entry)
                    file_summary["classes"].append(cls["name"])

                for func in data["functions"]:
                    func_entry = {
                        "file": file_key,
                        "name": func["name"],
                        "start_line": func["start_line"],
                        "end_line": func["end_line"],
                        "async": func["async"],
                        "parameters": func["parameters"],
                        "returns": func["returns"],
                        "decorators": func["decorators"],
                        "docstring": func["docstring"],
                    }
                    all_functions.append(func_entry)
                    file_summary["functions"].append(func["name"])

                for imp in data["imports"]:
                    all_imports.append({
                        "file": file_key,
                        **imp,
                    })
                    if imp.get("alias"):
                        file_summary["imports"].append(f"{imp['name']} as {imp['alias']}")
                    else:
                        file_summary["imports"].append(imp["name"])

                by_file[file_key] = file_summary

        # 统计
        result["analysis"] = {
            "files_analyzed": len(py_files),
            "summary": {
                "total_classes": len(all_classes),
                "total_functions": len(all_functions),
                "total_imports": len(all_imports),
            },
            # 全局列表
            # classes/functions 截断展示，imports 和 by_file 必须完整（依赖图需要）
            "classes": all_classes[:500],
            "functions": all_functions[:500],
            "imports": all_imports,          # 不截断！dep graph 需要完整 import 数据
            # 按文件聚合（完整，dep graph 需要）
            "by_file": dict(by_file),
        }

        summary = result["analysis"]["summary"]
        print(f"  Classes: {summary['total_classes']} | Functions: {summary['total_functions']} | Imports: {summary['total_imports']}")

    result["elapsed_seconds"] = round(time.time() - t0, 2)
    print(f"\nTotal time: {result['elapsed_seconds']}s")

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Output: {output_path}")

    return result


def main():
    parser = argparse.ArgumentParser(description="Analyze repository structure with Python AST")
    parser.add_argument("repo_path", help="Path to repository")
    parser.add_argument("--output", "-o", help="Output JSON file")
    parser.add_argument("--max-files", type=int, default=300, help="Max Python files")
    args = parser.parse_args()
    analyze_repo(args.repo_path, max_files=args.max_files, output_path=args.output)


if __name__ == "__main__":
    main()
