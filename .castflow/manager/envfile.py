"""One gitignored env file for project secrets.

Every optional integration reads and writes keys here. Do not put secrets in
config.json. The file is `.castflow-runtime/secrets.env`.
"""

from __future__ import print_function

import os
import re

ENV_NAME = "secrets.env"
_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def env_path(project_root):
    return os.path.join(project_root or "", ".castflow-runtime", ENV_NAME)


def _parse(text):
    found = {}
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        if not _NAME.match(name):
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        found[name] = value
    return found


def load(project_root):
    """Return `{NAME: value}`. Missing file is an empty map."""
    path = env_path(project_root)
    if not project_root or not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            return _parse(handle.read())
    except OSError:
        return {}


def get(project_root, name):
    if not _NAME.match(name or ""):
        return None
    value = load(project_root).get(name)
    if value is None or not str(value).strip():
        return None
    return str(value).strip()


def set_key(project_root, name, value):
    """Insert or replace one key. Other keys and comments stay. Returns False if rejected."""
    if not project_root or not _NAME.match(name or ""):
        return False
    text = "" if value is None else str(value).strip()
    if not text or "\n" in text or "\r" in text:
        return False
    path = env_path(project_root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    existing = ""
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                existing = handle.read()
        except OSError:
            existing = ""
    prefix = name + "="
    export_prefix = "export " + name + "="
    lines = existing.splitlines()
    out = []
    replaced = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(prefix) or stripped.startswith(export_prefix):
            if not replaced:
                out.append(prefix + text)
                replaced = True
            continue
        out.append(line)
    if not replaced:
        if out and out[-1].strip():
            out.append("")
        out.append(prefix + text)
    body = "\n".join(out)
    if not body.endswith("\n"):
        body += "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(body)
    return True
