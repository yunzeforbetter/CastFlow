#!/usr/bin/env python3
"""CastFlow manager entry: launch/setup, seed, ui, skills, retire, update, sync."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from manager.cli import main

if __name__ == "__main__":
    sys.exit(main() or 0)
