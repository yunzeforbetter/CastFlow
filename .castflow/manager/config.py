"""Runtime config.json: evolution plugin + adapter projection flags."""

import json
import os

from .paths import ensure_runtime_layout, runtime_path

CONFIG_VERSION = 1

DEFAULT_CONFIG = {
    "version": CONFIG_VERSION,
    "language": "zh",
    "evolution": {"enabled": True},
    "adapters": {
        "claude": True,
        "grok": True,
        "codex": True,
        "cursor": True,
    },
    "generate_skills": False,
    "generate_prompt": "",
    "inbound_memory": {
        "claude_auto_memory": False,
        "grok_memory": False,
    },
}


def default_config():
    data = json.loads(json.dumps(DEFAULT_CONFIG))
    return data


def _deep_merge(base, override):
    if not isinstance(override, dict):
        return base
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_config(project_root):
    path = runtime_path(project_root, "config")
    data = default_config()
    if not os.path.isfile(path):
        return data
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            data = _deep_merge(data, loaded)
    except (json.JSONDecodeError, OSError):
        pass
    data["version"] = CONFIG_VERSION
    return data


def save_config(project_root, config):
    ensure_runtime_layout(project_root)
    path = runtime_path(project_root, "config")
    payload = _deep_merge(default_config(), config or {})
    payload["version"] = CONFIG_VERSION
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return payload


def evolution_enabled(project_root):
    return bool(load_config(project_root).get("evolution", {}).get("enabled", True))


def set_evolution(project_root, enabled):
    config = load_config(project_root)
    config.setdefault("evolution", {})["enabled"] = bool(enabled)
    return save_config(project_root, config)
