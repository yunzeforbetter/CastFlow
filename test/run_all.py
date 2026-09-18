#!/usr/bin/env python3
"""Run the full CastFlow regression suite (unittest + origin-evolve verifier)."""

from __future__ import print_function

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASTFLOW = os.path.join(ROOT, ".castflow")


def run(title, args, cwd=None):
    print("\n=== {} ===".format(title))
    print(" ".join(args))
    rc = subprocess.call(args, cwd=cwd or ROOT)
    if rc != 0:
        print("FAIL: {} (exit {})".format(title, rc))
    else:
        print("PASS: {}".format(title))
    return rc


def main():
    py = sys.executable
    failures = 0
    failures += run(
        "unittest discover",
        [py, "-m", "unittest", "discover", "-s", "test", "-p", "test_*.py", "-t", ROOT],
        cwd=ROOT,
    )
    failures += run(
        "origin-evolve verify_redesign",
        [py, os.path.join("test", "origin-evolve", "verify_redesign.py")],
        cwd=ROOT,
    )
    failures += run(
        "trace-flush --selftest",
        [py, os.path.join(CASTFLOW, "core", "hooks", "trace-flush.py"), "--selftest"],
        cwd=ROOT,
    )
    print("\n==========")
    if failures:
        print("SUITE FAILED")
        return 1
    print("SUITE PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
