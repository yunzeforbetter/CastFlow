"""Runtime config.json: evolution plugin + adapter projection flags."""

import json
import os

from .paths import ensure_runtime_layout, runtime_path

CONFIG_VERSION = 1

DEFAULT_CONFIG = {
    "version": CONFIG_VERSION,
    "language": "en",
    "evolution": {"enabled": True},
    "adapters": {
        "claude": True,
        "grok": True,
        "codex": True,
        "cursor": True,
    },
    "generate_skills": False,
    "generate_prompt": "",
    "jev_enabled": False,
    "inbound_memory": {
        "claude_auto_memory": False,
        "grok_memory": False,
    },
}


def normalize_language(language):
    """Cold-start language. Missing or en is English. zh stays Chinese."""
    text = str(language or "").strip().lower().replace("_", "-")
    if not text or text == "en" or text.startswith("en-"):
        return "en"
    if text in ("zh", "cn", "chinese") or text.startswith("zh-"):
        return "zh"
    return text.split("-", 1)[0]


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
    data.pop("jev_key", None)
    data.pop("TYPESAFE_API_KEY", None)
    return data


def save_config(project_root, config):
    ensure_runtime_layout(project_root)
    path = runtime_path(project_root, "config")
    payload = _deep_merge(default_config(), config or {})
    payload["version"] = CONFIG_VERSION
    payload.pop("jev_key", None)
    payload.pop("TYPESAFE_API_KEY", None)
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
