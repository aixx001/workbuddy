#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 4: Repository Selection
Select the best repository based on scoring
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR.parent / 'outputs' / '03_analysis'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_analysis():
    """Load analysis from stage 3"""
    analysis_path = SCRIPT_DIR.parent / 'outputs' / '03_analysis' / 'analysis_report.json'
    if analysis_path.exists():
        with open(analysis_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def score_repo(analysis: dict) -> float:
    """Score a repository"""
    score = 0
    repo_info = analysis.get('repo_info', {})
    analysis_data = analysis

    # Stars weight (max 40 points)
    stars = repo_info.get('stars', 0)
    score += min(stars / 50, 40)

    # Python files (max 20 points)
    py_files = analysis_data.get('python_files', 0)
    score += min(py_files / 2, 20)

    # Has README (10 points)
    if analysis_data.get('has_readme'):
        score += 10

    # Has requirements (10 points)
    if analysis_data.get('has_requirements'):
        score += 10

    # License compatibility (10 points)
    license = repo_info.get('license', '')
    if license in ['MIT', 'Apache-2.0', 'BSD-3-Clause']:
        score += 10

    return round(score, 2)


def main():
    parser = argparse.ArgumentParser(description='Stage 4: Repo Selection')
    parser.add_argument('--analysis-file', type=str, help='Analysis JSON file')
    parser.add_argument('--output', type=str, help='Output JSON path')
    parser.add_argument('--top', type=int, default=3, help='Top N candidates')

    args = parser.parse_args()

    # Load analysis
    if args.analysis_file:
        with open(args.analysis_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            analyses = data.get('analyses', [])
    else:
        data = load_analysis()
        analyses = data.get('analyses', []) if data else []

    if not analyses:
        print("[ERROR] No analysis found. Run stage 3 first.")
        sys.exit(1)

    print("\n" + "="*60)
    print("[STAGE 4] Repository Selection")
    print("="*60)

    # Score all repos
    scored = []
    for analysis in analyses:
        score = score_repo(analysis)
        analysis['final_score'] = score
        scored.append(analysis)

    # Sort by score
    scored.sort(key=lambda x: x['final_score'], reverse=True)

    # Take top N
    top_repos = scored[:args.top]

    print(f"\n[SCORED REPOSITORIES]")
    for i, repo in enumerate(scored, 1):
        print(f"   {i}. {repo.get('name')} - Score: {repo.get('final_score')}")

    print(f"\n[TOP {len(top_repos)} SELECTED]")
    for i, repo in enumerate(top_repos, 1):
        print(f"   {i}. {repo.get('name')}")
        print(f"      Path: {repo.get('path')}")
        print(f"      Score: {repo.get('final_score')}")

    # Save result
    result = {
        'selected_at': datetime.now().isoformat(),
        'total_scored': len(scored),
        'selected': top_repos,
        'all_scores': [{'name': r.get('name'), 'score': r.get('final_score')} for r in scored]
    }

    output_path = args.output or OUTPUT_DIR / 'final_repo.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n[SAVED] {output_path}")
    return result


if __name__ == '__main__':
    main()
