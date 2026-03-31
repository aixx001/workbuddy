#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Repo Reuse Flow - Main Entry Script
Workflow: Demand -> Search -> Analyze -> Select -> Extract -> Generate
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Fix Windows encoding issue
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add scripts dir to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))


def run_stage(stage_num: int, stage_name: str, script_name: str, **kwargs):
    """Run a single stage"""
    print(f"\n{'='*60}")
    print(f"[Stage {stage_num}] {stage_name}")
    print(f"{'='*60}")

    script_path = SCRIPT_DIR / script_name
    if not script_path.exists():
        print(f"[ERROR] Script not found: {script_path}")
        return False

    # Build command
    cmd = [sys.executable, str(script_path)]

    # Add arguments
    for key, value in kwargs.items():
        if value is not None:
            if isinstance(value, bool) and value:
                cmd.append(f"--{key.replace('_', '-')}")
            elif isinstance(value, list):
                for v in value:
                    cmd.append(f"--{key.replace('_', '-')}")
                    cmd.append(str(v))
            else:
                cmd.append(f"--{key.replace('_', '-')}")
                cmd.append(str(value))

    print(f"Command: {' '.join(cmd)}")

    # Execute script
    result = os.system(' '.join(cmd))

    if result != 0:
        print(f"[FAIL] Stage {stage_num} failed")
        return False

    print(f"[OK] Stage {stage_num} completed")
    return True


def main():
    parser = argparse.ArgumentParser(description='Repo Reuse Flow - Open Source Project Reuse Workflow')
    parser.add_argument('--project-path', type=str, help='Existing project path')
    parser.add_argument('--keywords', type=str, nargs='+', help='GitHub search keywords')
    parser.add_argument('--min-stars', type=int, default=100, help='Minimum stars')
    parser.add_argument('--max-candidates', type=int, default=10, help='Max candidates')
    parser.add_argument('--start-stage', type=int, default=1, choices=[1,2,3,4,5,6], help='Start from stage')
    parser.add_argument('--end-stage', type=int, default=6, choices=[1,2,3,4,5,6], help='End at stage')
    parser.add_argument('--skip-stages', type=str, help='Skip stages, comma separated')

    args = parser.parse_args()

    # Parse skipped stages
    skip_stages = set()
    if args.skip_stages:
        skip_stages = set(int(s) for s in args.skip_stages.split(','))

    print("=== Repo Reuse Flow Started ===")
    print(f"Range: Stage {args.start_stage} -> Stage {args.end_stage}")
    if skip_stages:
        print(f"Skip: {skip_stages}")

    # Create output directory
    output_dir = SCRIPT_DIR.parent / 'outputs'
    output_dir.mkdir(exist_ok=True)

    # Stage 1: Demand Collection
    if args.start_stage <= 1 <= args.end_stage and 1 not in skip_stages:
        success = run_stage(1, "Demand Collection", "01_demand_collect.py",
                          project_path=args.project_path)
        if not success and args.start_stage == 1:
            sys.exit(1)

    # Stage 2: Repo Search
    if args.start_stage <= 2 <= args.end_stage and 2 not in skip_stages:
        success = run_stage(2, "Repo Search", "02_repo_search.py",
                          keywords=args.keywords,
                          min_stars=args.min_stars,
                          max_candidates=args.max_candidates)
        if not success:
            if input("Stage 2 failed, continue? (y/n): ").lower() != 'y':
                sys.exit(1)

    # Stage 3: Repo Analysis
    if args.start_stage <= 3 <= args.end_stage and 3 not in skip_stages:
        success = run_stage(3, "Repo Analysis", "03_repo_analyze.py")
        if not success:
            if input("Stage 3 failed, continue? (y/n): ").lower() != 'y':
                sys.exit(1)

    # Stage 4: Repo Selection
    if args.start_stage <= 4 <= args.end_stage and 4 not in skip_stages:
        success = run_stage(4, "Repo Selection", "04_repo_select.py")
        if not success:
            sys.exit(1)

    # Stage 5: Module Extraction
    if args.start_stage <= 5 <= args.end_stage and 5 not in skip_stages:
        success = run_stage(5, "Module Extraction", "05_module_extract.py")
        if not success:
            sys.exit(1)

    # Stage 6: Integration Plan
    if args.start_stage <= 6 <= args.end_stage and 6 not in skip_stages:
        success = run_stage(6, "Integration Plan", "06_integration_generate.py",
                          project_path=args.project_path)
        if not success:
            sys.exit(1)

    print(f"\n{'='*60}")
    print("[DONE] All stages completed!")
    print(f"Output: {output_dir}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
