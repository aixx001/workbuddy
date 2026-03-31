#!/usr/bin/env python3
"""
payload_api.py — Module Market Payload CMS 数据管理

统一入口，所有 CMS 数据操作通过 REST API 完成。
不依赖 TypeScript 编译，不需要 npx tsx。

Usage:
    python payload_api.py list                          # 列出所有模块
    python payload_api.py get <slug>                    # 查看单个模块
    python payload_api.py update-status <slug> <status> # 更新状态
    python payload_api.py upsert-module <slug>          # 从 JSON 文件上架/更新模块
    python payload_api.py sync-all                      # 同步全部 seed 数据
    python payload_api.py schema                        # 查看 status 允许值

Prerequisites:
    Payload dev server running: pnpm dev (port 3000)
"""

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import quote

import httpx

# ============================================================
# 配置
# ============================================================

API_BASE = "http://localhost:3000/api"
TIMEOUT = 10

# 允许的 status 值（与 Modules.ts schema 同步）
VALID_STATUSES = {"draft", "testing", "active", "published", "migrated", "archived"}


# ============================================================
# Payload REST API Client
# ============================================================

class PayloadClient:
    """Payload CMS REST API 客户端"""

    def __init__(self, base_url: str = API_BASE):
        self.base_url = base_url
        self.client = httpx.Client(timeout=TIMEOUT)

    # ── 模块操作 ──────────────────────────────────────────

    def list_modules(self, limit: int = 50) -> list[dict]:
        """列出所有模块"""
        resp = self.client.get(f"{self.base_url}/modules", params={"limit": limit})
        resp.raise_for_status()
        return resp.json().get("docs", [])

    def get_module(self, slug: str) -> dict | None:
        """按 slug 查找模块"""
        resp = self.client.get(
            f"{self.base_url}/modules",
            params={"where[slug][equals]": slug, "limit": 1},
        )
        resp.raise_for_status()
        docs = resp.json().get("docs", [])
        return docs[0] if docs else None

    def update_module(self, module_id: int, data: dict) -> dict:
        """更新模块"""
        resp = self.client.patch(
            f"{self.base_url}/modules/{module_id}",
            json=data,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()

    def create_module(self, data: dict) -> dict:
        """创建模块"""
        resp = self.client.post(
            f"{self.base_url}/modules",
            json=data,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()

    def upsert_module(self, slug: str, data: dict) -> dict:
        """创建或更新模块"""
        existing = self.get_module(slug)
        if existing:
            return self.update_module(existing["id"], data)
        else:
            data["slug"] = slug
            return self.create_module(data)

    def update_module_status(self, slug: str, status: str) -> dict:
        """更新模块状态"""
        if status not in VALID_STATUSES:
            raise ValueError(f"无效状态 '{status}'，允许: {VALID_STATUSES}")
        mod = self.get_module(slug)
        if not mod:
            raise ValueError(f"模块 '{slug}' 不存在")
        return self.update_module(mod["id"], {"status": status})

    # ── 仓库操作 ──────────────────────────────────────────

    def list_repos(self, limit: int = 50) -> list[dict]:
        """列出所有仓库"""
        resp = self.client.get(f"{self.base_url}/repos", params={"limit": limit})
        resp.raise_for_status()
        return resp.json().get("docs", [])

    def upsert_repo(self, name: str, data: dict) -> dict:
        """创建或更新仓库"""
        resp = self.client.get(
            f"{self.base_url}/repos",
            params={"where[name][equals]": name, "limit": 1},
        )
        resp.raise_for_status()
        docs = resp.json().get("docs", [])
        if docs:
            r = self.client.patch(
                f"{self.base_url}/repos/{docs[0]['id']}",
                json=data,
                headers={"Content-Type": "application/json"},
            )
        else:
            data["name"] = name
            r = self.client.post(
                f"{self.base_url}/repos",
                json=data,
                headers={"Content-Type": "application/json"},
            )
        r.raise_for_status()
        return r.json()


# ============================================================
# CLI 命令
# ============================================================

def cmd_list(client: PayloadClient, args):
    """列出所有模块"""
    modules = client.list_modules()
    if not modules:
        print("（空）没有模块")
        return

    # 表头
    print(f"{'Slug':<30} {'Category':<15} {'Status':<10} {'Type':<8} {'Score':>5}")
    print("─" * 70)
    for m in modules:
        print(
            f"{m.get('slug', '?'):<30} "
            f"{m.get('category', '?'):<15} "
            f"{m.get('status', '?'):<10} "
            f"{m.get('moduleType', '?'):<8} "
            f"{m.get('reuseScore', 0):>5.2f}"
        )
    print(f"\n共 {len(modules)} 个模块")


def cmd_get(client: PayloadClient, args):
    """查看单个模块"""
    mod = client.get_module(args.slug)
    if not mod:
        print(f"❌ 模块 '{args.slug}' 不存在")
        sys.exit(1)
    # 精简输出
    keys = ["id", "name", "slug", "moduleType", "category", "status",
            "reuseScore", "demoEndpoint", "installCmd", "sourceRepo"]
    for k in keys:
        if k in mod and mod[k]:
            print(f"  {k}: {mod[k]}")


def cmd_update_status(client: PayloadClient, args):
    """更新模块状态"""
    try:
        result = client.update_module_status(args.slug, args.status)
        doc = result.get("doc", result)
        print(f"✅ {args.slug} → {args.status}")
        print(f"   id={doc.get('id')} name={doc.get('name')}")
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP {e.response.status_code}: {e.response.text[:200]}")
        sys.exit(1)


def cmd_upsert_module(client: PayloadClient, args):
    """从 JSON 文件上架/更新模块"""
    json_path = Path(args.json_file)
    if not json_path.exists():
        print(f"❌ 文件不存在: {json_path}")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    slug = data.get("slug", args.slug)
    if not slug:
        print("❌ 缺少 slug")
        sys.exit(1)

    try:
        result = client.upsert_module(slug, data)
        doc = result.get("doc", result)
        print(f"✅ Upserted: {slug}")
        print(f"   id={doc.get('id')} status={doc.get('status')}")
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP {e.response.status_code}: {e.response.text[:200]}")
        sys.exit(1)


def cmd_sync_all(client: PayloadClient, args):
    """同步全部 seed 数据（调用 npx tsx）"""
    import subprocess
    payload_dir = Path(__file__).resolve().parents[2] / "outputs" / "06_module_market" / "payload"
    print(f"📁 Payload 目录: {payload_dir}")
    print("🔄 运行 seed-modules.ts ...")
    result = subprocess.run(
        ["npx", "tsx", "src/seed/seed-modules.ts"],
        cwd=str(payload_dir),
        capture_output=True,
        text=True,
        timeout=30,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"⚠️  stderr: {result.stderr[:300]}")
    print("✅ 同步完成" if result.returncode == 0 else "❌ 同步失败")


def cmd_schema(client: PayloadClient, args):
    """查看 status 允许值"""
    print("Module status 允许值:")
    for s in sorted(VALID_STATUSES):
        print(f"  - {s}")
    print(f"\n共 {len(VALID_STATUSES)} 个状态")


# ============================================================
# 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Module Market Payload CMS 数据管理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", help="可用命令")

    # list
    sub.add_parser("list", help="列出所有模块")

    # get
    p_get = sub.add_parser("get", help="查看单个模块")
    p_get.add_argument("slug", help="模块 slug")

    # update-status
    p_status = sub.add_parser("update-status", help="更新模块状态")
    p_status.add_argument("slug", help="模块 slug")
    p_status.add_argument("status", choices=sorted(VALID_STATUSES), help="目标状态")

    # upsert-module
    p_upsert = sub.add_parser("upsert-module", help="从 JSON 文件上架/更新模块")
    p_upsert.add_argument("slug", help="模块 slug")
    p_upsert.add_argument("--json-file", "-f", required=True, help="JSON 数据文件路径")

    # sync-all
    sub.add_parser("sync-all", help="同步全部 seed 数据")

    # schema
    sub.add_parser("schema", help="查看 schema 信息")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    client = PayloadClient()

    commands = {
        "list": cmd_list,
        "get": cmd_get,
        "update-status": cmd_update_status,
        "upsert-module": cmd_upsert_module,
        "sync-all": cmd_sync_all,
        "schema": cmd_schema,
    }

    commands[args.command](client, args)


if __name__ == "__main__":
    main()
