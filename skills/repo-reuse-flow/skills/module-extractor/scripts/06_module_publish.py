#!/usr/bin/env python3
"""
06_module_publish.py — 将提取的模块发布到 Payload CMS 模块市场

基于 outputs/06_module_market 的 Payload CMS 数据模型生成数据

Usage:
    # 预览模块数据（不发布）
    python 06_module_publish.py --module ragflow_common --preview

    # 生成 Payload CMS 导入 JSON
    python 06_module_publish.py --module ragflow_common --export-json

    # 调用 Payload CMS API 发布
    python 06_module_publish.py --module ragflow_common --cms-url http://localhost:3000 --api-key YOUR_KEY

    # 批量处理所有已提取模块
    python 06_module_publish.py --batch --cms-url http://localhost:3000 --api-key YOUR_KEY
"""

import argparse
import json
import sys
import zipfile
import hashlib
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SCRIPT_DIR = Path(__file__).parent
EXTRACTED_DIR = SCRIPT_DIR.parent / 'outputs' / '05_modules' / 'extracted_modules'
MARKET_DIR = SCRIPT_DIR.parent / 'outputs' / '06_module_market'
EXPORT_DIR = MARKET_DIR / 'exports'


def calculate_file_hash(filepath: Path) -> str:
    """计算文件的 SHA256 哈希"""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def collect_module_files(module_path: Path) -> list[dict]:
    """收集模块中的所有文件信息"""
    files = []
    for filepath in module_path.rglob('*'):
        if filepath.is_file() and not filepath.name.startswith('.'):
            rel_path = filepath.relative_to(module_path)
            files.append({
                'path': str(rel_path),
                'size': filepath.stat().st_size,
                'hash': calculate_file_hash(filepath)
            })
    return files


def infer_category(module_name: str, files: list[dict]) -> str:
    """根据模块名和文件内容推断分类"""
    name_lower = module_name.lower()

    # 基于模块名的启发式分类
    if any(k in name_lower for k in ['llm', 'chat', 'model', 'generator']):
        return 'llm'
    if any(k in name_lower for k in ['embed', 'embedding', 'vector']):
        return 'embeddings'
    if any(k in name_lower for k in ['retrieve', 'rag', 'search', 'index']):
        return 'retrievers'
    if any(k in name_lower for k in ['load', 'parser', 'document', 'pdf', 'doc']):
        return 'document-loaders'
    if any(k in name_lower for k in ['callback', 'trace', 'observe', 'monitor']):
        return 'callbacks'
    if any(k in name_lower for k in ['parse', 'output', 'format']):
        return 'output-parsers'
    if any(k in name_lower for k in ['util', 'common', 'base', 'tool']):
        return 'utilities'

    return 'other'


def infer_tags(module_name: str, files: list[dict]) -> list[str]:
    """推断模块标签"""
    tags = []
    name_lower = module_name.lower()

    # 基于名称
    if 'rag' in name_lower:
        tags.append('RAG')
    if 'common' in name_lower:
        tags.append('utility')
    if 'base' in name_lower:
        tags.append('foundation')

    # 基于文件
    file_names = [f['path'].lower() for f in files]
    if any('enum' in f for f in file_names):
        tags.append('enum')
    if any('const' in f for f in file_names):
        tags.append('constants')
    if any('config' in f for f in file_names):
        tags.append('configuration')
    if any('exception' in f for f in file_names):
        tags.append('error-handling')
    if any('limiter' in f for f in file_names):
        tags.append('rate-limiting')

    return list(set(tags))[:5]  # 最多5个标签


def extract_classes_from_manifest(manifest: dict) -> list[dict]:
    """从 manifest 中提取类信息"""
    classes = []
    files = manifest.get('files', [])

    for file_info in files:
        file_path = file_info.get('path', '')
        if file_path.endswith('.py') and 'classes' in file_info:
            for cls in file_info.get('classes', []):
                classes.append({
                    'className': cls.get('name', ''),
                    'sourceFile': file_path
                })

    return classes


def generate_module_data(module_path: Path) -> dict:
    """生成 Payload CMS Modules Collection 数据"""

    # 读取 manifest.json
    manifest_path = module_path / 'manifest.json'
    if manifest_path.exists():
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
    else:
        manifest = {}

    # 收集文件信息
    files = collect_module_files(module_path)
    module_name = module_path.name

    # 读取 requirements.txt
    requirements = []
    req_file = module_path / 'requirements.txt'
    if req_file.exists():
        with open(req_file, 'r', encoding='utf-8') as f:
            requirements = [
                {'package': line.strip().split('==')[0].split('>=')[0].split('<=')[0].strip(),
                 'version': line.strip().split('==')[1] if '==' in line else ''}
                for line in f
                if line.strip() and not line.startswith('#') and not line.startswith('-')
            ]

    # 统计代码行数
    total_lines = 0
    for filepath in module_path.rglob('*.py'):
        if filepath.is_file():
            with open(filepath, 'r', encoding='utf-8') as f:
                total_lines += len(f.readlines())

    # 生成 slug
    slug = module_name.lower().replace('_', '-').replace('ragflow-', '')

    # 生成 Modules Collection 数据
    module_data = {
        'name': manifest.get('name', module_name),
        'slug': slug,
        'description': manifest.get('description', f'从 {manifest.get("source_repo", "未知来源")} 提取的可复用模块，包含 {len(files)} 个文件，约 {total_lines} 行代码'),
        'sourceRepo': manifest.get('source_repo', ''),
        'reuseScore': manifest.get('reuse_score', 0.5),
        'category': infer_category(module_name, files),
        'tags': [{'tag': t} for t in infer_tags(module_name, files)],
        'externalDeps': requirements,
        'fileCount': len(files),
        'classes': extract_classes_from_manifest(manifest),
        'manifest': manifest,
        'status': 'draft'
    }

    return module_data


def generate_version_data(module_path: Path, version: str = "1.0.0") -> dict:
    """生成 Payload CMS Versions Collection 数据"""

    # 生成 ZIP 包
    zip_name = f"{module_path.name}_{version}.zip"
    zip_path = EXPORT_DIR / zip_name
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filepath in module_path.rglob('*'):
            if filepath.is_file() and not filepath.name.startswith('.'):
                arcname = filepath.relative_to(module_path)
                zf.write(filepath, arcname)

    # 生成 Versions Collection 数据
    version_data = {
        'module': module_path.name,  # 关联的模块名，发布时需要查询 ID
        'version': version,
        'changelog': f'Initial release extracted from {module_path.name}',
        'files': str(zip_path),  # 本地路径，发布时需要上传
        'extractedFrom': {
            'commitHash': '',  # 从 manifest 获取
            'extractedAt': datetime.now().isoformat(),
            'toolVersion': '1.0.0'
        }
    }

    return version_data, zip_path


def publish_to_payload_cms(module_data: dict, version_data: dict, cms_url: str, api_key: str) -> dict:
    """调用 Payload CMS API 发布模块"""

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }

    result = {
        'module_id': None,
        'version_id': None,
        'success': False,
        'errors': []
    }

    # 1. 创建或更新 Module
    module_url = f"{cms_url}/api/modules"

    # 检查是否已存在
    existing = requests.get(
        module_url,
        headers=headers,
        params={'where[slug][equals]': module_data['slug']}
    )

    if existing.status_code == 200 and existing.json().get('totalDocs', 0) > 0:
        # 更新现有模块
        module_id = existing.json()['docs'][0]['id']
        resp = requests.patch(
            f"{module_url}/{module_id}",
            headers=headers,
            json=module_data
        )
        result['module_id'] = module_id
        print(f"  Updated module: {module_data['slug']} (ID: {module_id})")
    else:
        # 创建新模块
        resp = requests.post(module_url, headers=headers, json=module_data)
        if resp.status_code in [200, 201]:
            result['module_id'] = resp.json().get('doc', {}).get('id')
            print(f"  Created module: {module_data['slug']} (ID: {result['module_id']})")
        else:
            result['errors'].append(f"Module creation failed: {resp.text}")
            return result

    # 2. 上传文件并创建 Version
    if result['module_id'] and 'files' in version_data:
        # 上传文件到 Media collection
        zip_path = version_data.pop('files')
        files = {'file': (Path(zip_path).name, open(zip_path, 'rb'), 'application/zip')}
        media_resp = requests.post(
            f"{cms_url}/api/media",
            headers={'Authorization': f'Bearer {api_key}'},
            files=files
        )

        if media_resp.status_code in [200, 201]:
            version_data['files'] = media_resp.json().get('doc', {}).get('id')
        else:
            # 文件上传失败，继续但不阻塞
            print(f"  Warning: File upload failed, version will be created without file")

        # 创建 Version
        version_data['module'] = result['module_id']
        version_url = f"{cms_url}/api/versions"
        resp = requests.post(version_url, headers=headers, json=version_data)

        if resp.status_code in [200, 201]:
            result['version_id'] = resp.json().get('doc', {}).get('id')
            print(f"  Created version: {version_data['version']} (ID: {result['version_id']})")

    result['success'] = len(result['errors']) == 0
    return result


def list_extracted_modules() -> list[Path]:
    """列出所有已提取的模块"""
    if not EXTRACTED_DIR.exists():
        return []
    return [p for p in EXTRACTED_DIR.iterdir() if p.is_dir()]


def main():
    parser = argparse.ArgumentParser(description='发布模块到 Payload CMS 模块市场')
    parser.add_argument('--module', help='模块名称（目录名）')
    parser.add_argument('--batch', action='store_true', help='批量处理所有已提取模块')
    parser.add_argument('--preview', action='store_true', help='预览模块数据（不发布）')
    parser.add_argument('--export-json', action='store_true', help='导出 JSON 文件（不调用 API）')
    parser.add_argument('--cms-url', default='http://localhost:3000', help='Payload CMS URL')
    parser.add_argument('--api-key', help='Payload CMS API Key')
    parser.add_argument('--version', default='1.0.0', help='版本号')

    args = parser.parse_args()

    # 确定要处理的模块
    if args.batch:
        modules = list_extracted_modules()
        if not modules:
            print("No extracted modules found.")
            return
        print(f"Found {len(modules)} extracted modules: {[m.name for m in modules]}")
    elif args.module:
        module_path = EXTRACTED_DIR / args.module
        if not module_path.exists():
            print(f"Module not found: {args.module}")
            return
        modules = [module_path]
    else:
        parser.print_help()
        return

    # 处理每个模块
    for module_path in modules:
        print(f"\n{'='*60}")
        print(f"Processing: {module_path.name}")
        print('='*60)

        # 生成数据
        module_data = generate_module_data(module_path)
        version_data, zip_path = generate_version_data(module_path, args.version)

        if args.preview:
            print("\n[Modules Data]")
            print(json.dumps(module_data, indent=2, ensure_ascii=False, default=str))
            print("\n[Versions Data]")
            print(json.dumps(version_data, indent=2, ensure_ascii=False, default=str))
            print(f"\n[ZIP File] {zip_path} ({zip_path.stat().st_size / 1024:.1f} KB)")

        elif args.export_json:
            EXPORT_DIR.mkdir(parents=True, exist_ok=True)
            export_file = EXPORT_DIR / f"{module_path.name}_module.json"
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'module': module_data,
                    'version': version_data,
                    'zip_path': str(zip_path)
                }, f, indent=2, ensure_ascii=False, default=str)
            print(f"Exported to: {export_file}")

        elif args.cms_url and args.api_key:
            print(f"Publishing to: {args.cms_url}")
            result = publish_to_payload_cms(module_data, version_data, args.cms_url, args.api_key)
            if result['success']:
                print(f"\n✅ Successfully published {module_path.name}")
            else:
                print(f"\n❌ Failed: {result['errors']}")
        else:
            print("Please specify --cms-url and --api-key, or use --preview/--export-json")


if __name__ == '__main__':
    main()
