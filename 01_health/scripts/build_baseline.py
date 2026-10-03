"""
Build the healthy baseline: one row per plateau (operating point) across all health
files, plus the validation figure and a console sanity report.

This is a thin runner around the shared module common/health_baseline.py — the module
holds all the analysis code and is imported by every section of the repo.

Usage (from this folder):
    python build_baseline.py              # reads ../data/**/health_*Nm*rpm*.csv
    python build_baseline.py <folder>     # any folder searched recursively instead

Writes to ../outputs/: health_baseline_plateaus.csv, health_baseline_validation.png
"""
import os, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SECTION_DIR = os.path.dirname(SCRIPT_DIR)                 # 01_health/
REPO_ROOT = os.path.dirname(SECTION_DIR)
sys.path.insert(0, os.path.join(REPO_ROOT, "common"))     # the single shared module
import health_baseline as hb

DATA_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(SECTION_DIR, "data")
OUT_DIR = os.path.join(SECTION_DIR, "outputs")

if __name__ == "__main__":
    hb.main(DATA_DIR, OUT_DIR)
