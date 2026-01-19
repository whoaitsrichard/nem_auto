"""
Path Configuration for NEM Auto Project
========================================
Centralizes all file paths for portability across different machines.

Usage:
    from config import DATA_DIR, OUTPUT_DIR, FIGURES_DIR, DUID_MAP_PATH, get_data_file

Environment Variables:
    NEM_DATA_PATH: Path to the external data folder (e.g., Box sync folder)
                   If not set, defaults to local data/samples directory
"""

import os
from pathlib import Path

# =============================================================================
# PROJECT ROOT (derived from this file's location)
# =============================================================================
# This file is at: nem_auto/code/config.py
# Project root is: nem_auto/
PROJECT_ROOT = Path(__file__).parent.parent

# =============================================================================
# EXTERNAL DATA DIRECTORY (Box folder or other external storage)
# =============================================================================
# Users should set the NEM_DATA_PATH environment variable to point to their
# local Box sync folder or wherever the large data files are stored.
#
# Example (add to ~/.bashrc or ~/.zshrc):
#   export NEM_DATA_PATH="/Users/yourname/Box/nem_data"
#
# On Windows:
#   set NEM_DATA_PATH=C:\Users\yourname\Box\nem_data
#
# If not set, falls back to local data/samples directory (for small test files)
DATA_DIR = Path(os.environ.get("NEM_DATA_PATH", PROJECT_ROOT / "data" / "samples"))

# =============================================================================
# PROJECT DIRECTORIES (relative to project root)
# =============================================================================
OUTPUT_DIR = PROJECT_ROOT / "output"
FIGURES_DIR = PROJECT_ROOT / "figures"

# Ensure output directories exist
OUTPUT_DIR.mkdir(exist_ok=True)
FIGURES_DIR.mkdir(exist_ok=True)

# =============================================================================
# DATA FILES
# =============================================================================
# DUID participant mapping file (in Box folder with other data)
DUID_MAP_FILENAME = "nem_duid_participant_map_2025-10-15.csv"
# Note: DUID map is in parent of DATA_DIR (nem_auto folder, not samples subfolder)
DUID_MAP_PATH = DATA_DIR.parent / DUID_MAP_FILENAME

# Large data files (in external Box folder)
BIDDAYOFFER_FILENAME = "PUBLIC_ARCHIVE#BIDDAYOFFER#FILE01#202510010000.csv"
BIDOFFERPERIOD_FILENAME = "PUBLIC_ARCHIVE#BIDOFFERPERIOD#FILE01#202510010000.CSV"
DISPATCHOFFERTRK_FILENAME = "PUBLIC_ARCHIVE#DISPATCHOFFERTRK#FILE01#202510010000.CSV"

# Full paths to data files
BIDDAYOFFER_PATH = DATA_DIR / BIDDAYOFFER_FILENAME
BIDOFFERPERIOD_PATH = DATA_DIR / BIDOFFERPERIOD_FILENAME
DISPATCHOFFERTRK_PATH = DATA_DIR / DISPATCHOFFERTRK_FILENAME


def get_data_file(filename: str) -> Path:
    """Get the full path to a data file in the external data directory."""
    return DATA_DIR / filename


def validate_data_paths() -> bool:
    """Check if required data files exist and print status."""
    files = [
        ("BIDDAYOFFER", BIDDAYOFFER_PATH),
        ("BIDOFFERPERIOD", BIDOFFERPERIOD_PATH),
        ("DISPATCHOFFERTRK", DISPATCHOFFERTRK_PATH),
        ("DUID_MAP", DUID_MAP_PATH),
    ]

    all_ok = True
    print("Data file validation:")
    for name, path in files:
        if path.exists():
            size_mb = path.stat().st_size / (1024**2)
            print(f"  [OK] {name}: {path} ({size_mb:.1f} MB)")
        else:
            print(f"  [MISSING] {name}: {path}")
            all_ok = False

    if not all_ok:
        print(f"\nHint: Set NEM_DATA_PATH environment variable to your data folder")
        print(f"Current DATA_DIR: {DATA_DIR}")

    return all_ok


# Print configuration when module is imported directly
if __name__ == "__main__":
    print("NEM Auto Project Configuration")
    print("=" * 50)
    print(f"PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"DATA_DIR: {DATA_DIR}")
    print(f"OUTPUT_DIR: {OUTPUT_DIR}")
    print(f"FIGURES_DIR: {FIGURES_DIR}")
    print(f"DUID_MAP_PATH: {DUID_MAP_PATH}")
    print()
    validate_data_paths()
