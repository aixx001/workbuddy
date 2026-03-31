#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 2: GitHub Repository Search
Search GitHub and filter high-quality candidate repositories
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR.parent / 'outputs' / '02_candidates'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

GITHUB_API = "https://api.github.com/search/repositories"


def load_config():
    """Load config file"""
    config_path = SCRIPT_DIR.parent / 'config' / 'settings.json'
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def search_github(keyword: str, min_stars: int = 100, max_results: int = 10, token: str = None):
    """Search GitHub repositories"""
    print(f"[SEARCH] Keyword: {keyword}")

    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    params = {
        "q": f"{keyword} in:name,description,readme",
        "sort": "stars",
        "order": "desc",
        "per_page": min(max_results, 100),
        "type": "public"
    }

    try:
        response = requests.get(GITHUB_API, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        repos = []
        for repo in data.get('items', []):
            repos.append({
                "name": repo['name'],
                "full_name": repo['full_name'],
                "description": repo.get('description', ''),
                "url": repo['html_url'],
                "stars": repo['stargazers_count'],
                "forks": repo['forks_count'],
                "language": repo.get('language', ''),
                "license": (repo.get('license') or {}).get('spdx_id', '') or '',
                "updated_at": repo['updated_at'],
                "open_issues": repo.get('open_issues_count', 0),
                "subscribers_count": repo.get('subscribers_count', 0),
                "search_keyword": keyword
            })

        print(f"   Found {len(repos)} repos")
        return repos

    except requests.exceptions.RequestException as e:
        print(f"   [ERROR] Search failed: {e}")
        return []


def filter_repos(repos: list, min_stars: int = 100, allowed_licenses: list = None) -> list:
    """Filter repositories"""
    if allowed_licenses is None:
        allowed_licenses = ["MIT", "Apache-2.0", "BSD-3-Clause", "BSD-2-Clause", "ISC", ""]

    filtered = []
    for repo in repos:
        if repo['stars'] < min_stars:
            continue
        license = repo.get('license', '')
        if license and license not in allowed_licenses:
            print(f"   [SKIP] {repo['name']}: license {license} not compatible")
            continue
        filtered.append(repo)

    return filtered


def rank_repos(repos: list) -> list:
    """Rank repositories by score"""
    for repo in repos:
        score = 0
        score += min(repo['stars'] / 100, 50)  # Stars weight
        score += min(repo['forks'] / 50, 20)    # Forks weight
        import datetime
        updated = datetime.datetime.strptime(repo['updated_at'], '%Y-%m-%dT%H:%M:%SZ')
        days_ago = (datetime.datetime.now() - updated).days
        if days_ago < 30:
            score += 15
        elif days_ago < 90:
            score += 10
        elif days_ago < 180:
            score += 5
        total = repo['stars'] + repo['forks']
        if total > 0:
            issue_ratio = repo['open_issues'] / total
            score += max(0, 15 - issue_ratio * 100)
        repo['score'] = round(score, 2)

    return sorted(repos, key=lambda x: x['score'], reverse=True)


def main():
    parser = argparse.ArgumentParser(description='Stage 2: GitHub Repo Search')
    parser.add_argument('--keywords', type=str, nargs='+', help='Search keywords')
    parser.add_argument('--demand-file', type=str, help='Demand file path')
    parser.add_argument('--min-stars', type=int, default=100, help='Minimum stars')
    parser.add_argument('--max-candidates', type=int, default=10, help='Max candidates')
    parser.add_argument('--output', type=str, help='Output JSON path')

    args = parser.parse_args()
    config = load_config()
    token = config.get('github_token')
    min_stars = args.min_stars or config.get('min_stars', 100)
    allowed_licenses = config.get('required_licenses', ["MIT", "Apache-2.0", "BSD-3-Clause"])

    keywords = args.keywords or []
    if not keywords and args.demand_file:
        with open(args.demand_file, 'r', encoding='utf-8') as f:
            demand = json.load(f)
            keywords = demand.get('generated_keywords', [])

    if not keywords:
        print("[ERROR] Please provide --keywords or --demand-file")
        sys.exit(1)

    print("\n" + "="*60)
    print("[STAGE 2] GitHub Repository Search")
    print("="*60)
    print(f"Min stars: {min_stars}")
    print(f"Keywords: {len(keywords)}")
    print()

    all_repos = []
    for keyword in keywords:
        repos = search_github(keyword, min_stars, args.max_candidates, token)
        all_repos.extend(repos)

    print(f"\n[TOTAL] Found {len(all_repos)} repos")

    # Deduplicate
    seen = set()
    unique_repos = []
    for repo in all_repos:
        if repo['full_name'] not in seen:
            seen.add(repo['full_name'])
            unique_repos.append(repo)

    print(f"[UNIQUE] {len(unique_repos)} repos")

    filtered_repos = filter_repos(unique_repos, min_stars, allowed_licenses)
    print(f"[FILTERED] {len(filtered_repos)} repos")

    ranked_repos = rank_repos(filtered_repos)
    final_repos = ranked_repos[:args.max_candidates]

    result = {
        "searched_at": datetime.now().isoformat(),
        "keywords": keywords,
        "total_found": len(unique_repos),
        "candidates": final_repos
    }

    output_path = args.output or OUTPUT_DIR / "candidates.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n[SAVED] {output_path}")
    print(f"\n[TOP {len(final_repos)}] Candidate Repositories:")
    for i, repo in enumerate(final_repos, 1):
        print(f"   {i}. {repo['name']} Stars:{repo['stars']} Lang:{repo['language']} License:{repo['license']}")

    return result


if __name__ == '__main__':
    main()
