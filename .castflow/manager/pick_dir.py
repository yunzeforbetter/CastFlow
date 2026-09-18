#!/usr/bin/env python3
"""Native folder picker. Prints the chosen path to stdout (UTF-8). Empty if cancelled."""

from __future__ import print_function

import os
import sys


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    initial = argv[0] if argv else os.getcwd()
    title = argv[1] if len(argv) > 1 else "Select project folder"
    if not initial or not os.path.isdir(initial):
        initial = os.path.expanduser("~")
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return 2
    root = tk.Tk()
    root.withdraw()
    try:
        root.update()
    except Exception:
        pass
    try:
        root.attributes("-topmost", True)
    except Exception:
        pass
    chosen = filedialog.askdirectory(
        initialdir=initial,
        title=title,
        mustexist=True,
    )
    try:
        root.destroy()
    except Exception:
        pass
    if not chosen:
        return 0
    path = os.path.abspath(chosen)
    out = getattr(sys.stdout, "buffer", None)
    payload = path.encode("utf-8")
    if out is not None:
        out.write(payload)
        out.flush()
    else:
        sys.stdout.write(path)
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
