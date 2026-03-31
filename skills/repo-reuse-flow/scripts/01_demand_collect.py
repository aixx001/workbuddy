#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 1: Demand Collection
Collect and structure user requirements
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

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR.parent / 'outputs' / '01_demand'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def collect_demand_interactive():
    """Interactive demand collection"""
    print("\n" + "="*60)
    print("[STAGE 1] Demand Collection")
    print("="*60)

    demand = {}

    print("\n[1/6] Business Goal")
    print("What is your main business goal?")
    demand['business_goal'] = input("> ").strip()

    print("\n[2/6] Existing Project")
    print("Path to your existing project (or 'none'):")
    demand['existing_project'] = input("> ").strip()
    if demand['existing_project'].lower() == 'none':
        demand['existing_project'] = None

    print("\n[3/6] Pain Points")
    print("What are the current pain points? (comma separated)")
    demand['pain_points'] = [p.strip() for p in input("> ").split(',') if p.strip()]

    print("\n[4/6] Technical Constraints")
    print("Any technical constraints? (comma separated)")
    demand['constraints'] = [c.strip() for c in input("> ").split(',') if c.strip()]

    print("\n[5/6] Preferred Language")
    print("Preferred programming language (default: Python):")
    demand['language'] = input("> ").strip() or "Python"

    print("\n[6/6] Search Keywords")
    print("What keywords to search on GitHub? (comma separated)")
    demand['search_keywords'] = [k.strip() for k in input("> ").split(',') if k.strip()]

    # Generate refined keywords
    keywords = demand.get('search_keywords', [])
    keywords.append(demand.get('language', 'Python'))
    if demand.get('pain_points'):
        keywords.extend(demand.get('pain_points', []))
    demand['generated_keywords'] = list(set(keywords))

    return demand


def main():
    parser = argparse.ArgumentParser(description='Stage 1: Demand Collection')
    parser.add_argument('--project-path', type=str, help='Existing project path')
    parser.add_argument('--output', type=str, help='Output JSON path')
    parser.add_argument('--auto', action='store_true', help='Auto mode with sample data')

    args = parser.parse_args()

    if args.auto or args.project_path:
        # Auto mode
        demand = {
            'business_goal': 'Build a REST API backend',
            'existing_project': args.project_path,
            'pain_points': ['slow development', 'missing features'],
            'constraints': ['must be fast', 'easy to maintain'],
            'language': 'Python',
            'search_keywords': ['FastAPI', 'REST API'],
            'generated_keywords': ['FastAPI', 'REST API', 'Python']
        }
    else:
        demand = collect_demand_interactive()

    print("\n[DEMAND SUMMARY]")
    print(json.dumps(demand, indent=2, ensure_ascii=False))

    output_path = args.output or OUTPUT_DIR / "demand.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(demand, f, ensure_ascii=False, indent=2)

    print(f"\n[SAVED] {output_path}")
    return demand


if __name__ == '__main__':
    main()
