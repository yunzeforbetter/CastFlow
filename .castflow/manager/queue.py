"""Skill generation queue: sequential AI jobs driven by catalog."""

import json
import os

from .catalog import load_catalog, save_catalog
from .config import load_config, normalize_language
from .paths import ensure_runtime_layout, runtime_path

QUEUE_VERSION = 1
QUEUE_ITEM_STATES = frozenset(("queued", "running", "done", "failed"))


def empty_queue():
    return {"version": QUEUE_VERSION, "items": []}


def load_queue(project_root):
    path = runtime_path(project_root, "queue")
    if not os.path.isfile(path):
        return empty_queue()
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        if not isinstance(data, dict) or not isinstance(data.get("items"), list):
            return empty_queue()
        data["version"] = QUEUE_VERSION
        return data
    except (json.JSONDecodeError, OSError):
        return empty_queue()


def save_queue(project_root, queue):
    ensure_runtime_layout(project_root)
    path = runtime_path(project_root, "queue")
    payload = {
        "version": QUEUE_VERSION,
        "items": list(queue.get("items") or []),
    }
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return payload


def enqueue_accepted(project_root):
    """Build or refresh a sequential queue without dropping in-flight work."""
    catalog = load_catalog(project_root)
    old_queue = load_queue(project_root)
    old_by_id = {
        str(item.get("id")): item
        for item in old_queue.get("items") or []
        if isinstance(item, dict) and item.get("id")
    }
    items = []

    for mod in catalog.get("modules") or []:
        if mod.get("status") != "accepted":
            continue
        if mod.get("skill_state") == "ready":
            continue
        item = old_by_id.get(str(mod["id"]))
        if item and item.get("state") == "done":
            mod["skill_state"] = "ready"
            continue
        if item and item.get("state") in QUEUE_ITEM_STATES:
            items.append(dict(item))
        else:
            items.append({
                "kind": "module",
                "id": mod["id"],
                "skill": "programmer-{}-skill".format(mod["id"]),
                "state": "queued",
            })
        if items[-1].get("state") in ("queued", "running", "failed"):
            mod["skill_state"] = "queued"

    save_catalog(project_root, catalog)
    return save_queue(project_root, {"items": items})


def next_item(project_root):
    queue = load_queue(project_root)
    for item in queue.get("items") or []:
        if item.get("state") == "queued":
            return item
    return None


def _find_item(queue, name):
    wanted = str(name or "").strip()
    for item in queue.get("items") or []:
        if wanted in (str(item.get("id") or ""), str(item.get("skill") or "")):
            return item
    return None


def _save_item_state(project_root, name, state, error=""):
    if state not in QUEUE_ITEM_STATES:
        return {"ok": False, "error": "invalid queue state", "state": state}
    queue = load_queue(project_root)
    item = _find_item(queue, name)
    if item is None:
        return {"ok": False, "error": "unknown queue item", "name": name}
    item["state"] = state
    if error:
        item["error"] = str(error).strip()
    else:
        item.pop("error", None)
    save_queue(project_root, queue)
    catalog = load_catalog(project_root)
    for mod in catalog.get("modules") or []:
        if str(mod.get("id")) != str(item.get("id")):
            continue
        if state == "done":
            mod["skill_state"] = "ready"
        elif state == "failed":
            mod["skill_state"] = "failed"
        else:
            mod["skill_state"] = "queued"
        break
    save_catalog(project_root, catalog)
    return {"ok": True, "item": dict(item)}


def complete_item(project_root, name):
    """Validate one generated skill, then mark its queue item done."""
    queue = load_queue(project_root)
    item = _find_item(queue, name)
    if item is None:
        return {"ok": False, "error": "unknown queue item", "name": name}
    from installer.validate import check_programmer_skill, validate_skill_dir
    from .skills import project_skill_dir
    skill_name = item.get("skill") or "programmer-{}-skill".format(item.get("id"))
    skill_dir = project_skill_dir(project_root, skill_name)
    errors, _warnings, skipped = validate_skill_dir(skill_dir)
    if skipped:
        errors = list(errors) + ["skill is not a catalog skill"]
    if not errors and skill_name.startswith("programmer-"):
        errors = list(check_programmer_skill(skill_dir, project_root))
    if errors:
        return {"ok": False, "error": "validation failed", "errors": errors}
    return _save_item_state(project_root, name, "done")


def fail_item(project_root, name, error):
    return _save_item_state(project_root, name, "failed", error=error)


def retry_item(project_root, name):
    return _save_item_state(project_root, name, "queued")


def _is_zh(language):
    return normalize_language(language) == "zh"


LOOP_ENGINE_PROMPT_NAME = "MODULE_MARK_SYSTEM_PROMPT.md"
LOOP_ENGINE_RUNTIME_PATH = ".castflow-runtime/skills/" + LOOP_ENGINE_PROMPT_NAME


def default_scan_generate_prompt(project_root, language=None):
    """One-line /goal prompt.

    Names the loop-engine file and the config language for speech to the
    user. Skill prose still follows the queue card, not this line.
    """
    cfg = load_config(project_root)
    if language is None:
        language = cfg.get("language") or "en"
    lang = normalize_language(language)
    if lang == "zh":
        return (
            "/goal 读取并按照 {path} 执行。"
            "跟用户说话用 {lang}：多选的问题和每项说明用中文。"
            "模块 id 保持原样。技能正文仍按卡上的 language。"
        ).format(path=LOOP_ENGINE_RUNTIME_PATH, lang=lang)
    return (
        "/goal Read and follow {path}. "
        "Speak to the user in {lang}: the multi-select question and each "
        "option sentence use that language. "
        "Keep module ids as printed. Skill prose still follows the card language."
    ).format(path=LOOP_ENGINE_RUNTIME_PATH, lang=lang)


def resolve_generate_prompt(project_root, prompt=None, language=None):
    """User text if non-empty, otherwise the built-in scan-and-generate prompt."""
    text = "" if prompt is None else str(prompt).strip()
    if not text:
        text = (load_config(project_root).get("generate_prompt") or "").strip()
    if text:
        return text
    return default_scan_generate_prompt(project_root, language=language)


def build_handoff(project_root, generate=None, prompt=None):
    """Prompt to paste into Claude / Grok / Codex.

    generate=False: install-only. Empty string — no AI generation prompt.
    generate=True: user prompt, or the built-in scan-and-generate prompt.
    generate=None: one queued skill-creator item if any; else follow
    config.generate_skills (prompt vs empty).
    """
    cfg = load_config(project_root)
    language = normalize_language(cfg.get("language"))
    zh = language == "zh"
    if generate is True:
        return resolve_generate_prompt(
            project_root, prompt=prompt, language=language)
    if generate is False:
        return ""
    item = next_item(project_root)
    if item is None:
        if cfg.get("generate_skills"):
            return resolve_generate_prompt(
                project_root, prompt=prompt, language=language)
        return ""

    catalog = load_catalog(project_root)
    modules_by_id = dict((m["id"], m) for m in catalog.get("modules") or [])
    remaining = [
        i for i in (load_queue(project_root).get("items") or [])
        if i.get("state") == "queued"
    ]
    skill = item.get("skill") or item.get("id")
    extra = []
    if item.get("kind") == "module":
        mod = modules_by_id.get(item.get("id")) or {}
        paths = ", ".join(mod.get("paths") or [])
        if paths:
            extra.append(paths)
        notes = (mod.get("notes") or "").strip()
        if notes:
            extra.append(notes)
    detail = "\n".join(extra)
    if zh:
        body = (
            "用 skill-creator 只写这一个，然后停：{}\n"
            "\n"
            "写到 `castflow-skills/{}/`，必须有 SKILL.md 和 ITERATION_GUIDE.md；"
            "只有有真实内容时才加 EXAMPLES.md 或 SKILL_MEMORY.md。\n"
            "正文按 `.castflow-runtime/skills/SKILL_ITERATION.md`。\n"
            "写完：`python .castflow-runtime/manager.py validate`，通过后再 "
            "`python .castflow-runtime/manager.py queue-complete {}`\n"
            "不要写 `.claude/skills` 或 `.agents/skills`。\n"
            "禁止并行开下一个 skill。\n"
            "正文语言用 config 的 language（{lang}）。zh 写中文，en 写英文，缺省英文。"
        ).format(skill, skill, skill, lang=language)
        if detail:
            body += "\n\n" + detail
        body += "\n\n剩余 {} 项。下一轮再说 castflow generate skills。".format(
            len(remaining))
        return body
    body = (
        "skill-creator: write only this skill, then stop: {}\n"
        "\n"
        "Write `castflow-skills/{}/` with SKILL.md and ITERATION_GUIDE.md; "
        "add EXAMPLES.md or SKILL_MEMORY.md only when they contain real content.\n"
        "Body follows `.castflow-runtime/skills/SKILL_ITERATION.md`.\n"
        "Then: `python .castflow-runtime/manager.py validate`, then "
        "`python .castflow-runtime/manager.py queue-complete {}`\n"
        "Do not write `.claude/skills` or `.agents/skills`.\n"
        "Do not start the next skill in parallel.\n"
        "Prose language is config language ({lang}). "
        "zh is Chinese, en is English, missing means English."
    ).format(skill, skill, skill, lang=language)
    if detail:
        body += "\n\n" + detail
    body += "\n\n{} remaining. Next turn say castflow generate skills.".format(
        len(remaining))
    return body
