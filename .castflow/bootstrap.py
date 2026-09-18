#!/usr/bin/env python3
"""
CastFlow Bootstrap - legacy installer entry.

Preferred commands:
    python .castflow/manager.py launch
    python .castflow/manager.py seed
    python .castflow/manager.py ui

This file still wraps installer CLI (--validate, --dry-run, Phase A copies).
Scan is not a manager command; module discovery is the pasted /goal loop-engine prompt.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from installer.cli import main

if __name__ == "__main__":
    main()
