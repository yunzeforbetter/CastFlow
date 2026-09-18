#!/usr/bin/env python3
"""Native folder picker. Prints the chosen path to stdout (UTF-8). Empty if cancelled.

macOS uses osascript (no tkinter / python-tk required). Other platforms use
tkinter. Empty stdout with exit 0 means cancelled.
"""

from __future__ import print_function

import os
import subprocess
import sys


def _escape_as(text):
    return (text or "").replace("\\", "\\\\").replace('"', '\\"')


def darwin_choose_folder_script(initial, title):
    """AppleScript that returns a POSIX folder path, or empty if cancelled."""
    prompt = _escape_as(title)
    lines = ["try"]
    if initial and os.path.isdir(initial):
        default = _escape_as(os.path.abspath(initial))
        lines.append(
            '  set theFolder to choose folder with prompt "{}" '
            'default location (POSIX file "{}")'.format(prompt, default)
        )
    else:
        lines.append(
            '  set theFolder to choose folder with prompt "{}"'.format(prompt)
        )
    lines.extend([
        "  return POSIX path of theFolder",
        "on error",
        '  return ""',
        "end try",
    ])
    return "\n".join(lines)


def pick_darwin(initial, title):
    """Return ('ok', path), ('cancel', None), or ('unavailable', None)."""
    script = darwin_choose_folder_script(initial, title)
    try:
        proc = subprocess.Popen(
            ["osascript", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        out, _err = proc.communicate(script.encode("utf-8"))
    except OSError:
        return "unavailable", None
    text = (out or b"").decode("utf-8", "replace").strip().rstrip("/")
    if proc.returncode not in (0, None):
        return "unavailable", None
    if not text:
        return "cancel", None
    path = os.path.abspath(text)
    if not os.path.isdir(path):
        return "cancel", None
    return "ok", path


def pick_tkinter(initial, title):
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return None
    root = tk.Tk()
    root.withdraw()
    try:
        root.update()
    except Exception:
        pass
    try:
        root.lift()
        root.attributes("-topmost", True)
        root.focus_force()
    except Exception:
        pass
    kwargs = dict(initialdir=initial, title=title)
    try:
        chosen = filedialog.askdirectory(mustexist=True, **kwargs)
    except TypeError:
        chosen = filedialog.askdirectory(**kwargs)
    try:
        root.destroy()
    except Exception:
        pass
    return chosen or None


def _write_path(path):
    out = getattr(sys.stdout, "buffer", None)
    payload = path.encode("utf-8")
    if out is not None:
        out.write(payload)
        out.flush()
    else:
        sys.stdout.write(path)
        sys.stdout.flush()


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    initial = argv[0] if argv else os.getcwd()
    title = argv[1] if len(argv) > 1 else "Select project folder"
    if not initial or not os.path.isdir(initial):
        initial = os.path.expanduser("~")
    chosen = None
    if sys.platform == "darwin":
        status, path = pick_darwin(initial, title)
        if status == "ok":
            _write_path(path)
            return 0
        if status == "cancel":
            return 0
    chosen = pick_tkinter(initial, title)
    if chosen is None:
        # ImportError / no dialog: 2. Empty string from a shown dialog: cancel.
        try:
            import tkinter  # noqa: F401
        except ImportError:
            return 2
        return 0
    _write_path(os.path.abspath(chosen))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
