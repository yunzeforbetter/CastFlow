#!/usr/bin/env python3
"""
CastFlow Bootstrap - Deterministic File Generator

Thin wrapper that delegates to the bootstrap package.
Kept for backward compatibility so existing commands still work:
    python .castflow/bootstrap.py
    python .castflow/bootstrap.py --validate
    python .castflow/bootstrap.py --dry-run
    python .castflow/bootstrap.py --skill architect

The actual implementation lives in .castflow/bootstrap/ (Python package).
"""

import os
import sys

# Ensure the bootstrap package is importable from this script's directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bootstrap.cli import main

if __name__ == "__main__":
    main()
