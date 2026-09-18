---
name: bootstrap-skill
description: >
  Install CastFlow into this repo. Use when the user says bootstrap
  castflow or 初始化 CastFlow. NOT for writing module skill files
  (skill-creator).
---

# bootstrap-skill

Install CastFlow. **Cold start is the GUI**, not this conversation. Double-click `castflow.bat` (CastFlow repo root) or run `python CastFlow/.castflow/manager.py launch`. The wizard collects language / adapters / evolution, then copies framework files.

Simple cold start copies files only. Module discovery for generate is the **pasted prompt** (default: AI scans the project's product scripts, any language; **not** CastFlow / `.castflow` / `.castflow-runtime` / adapter trees). What counts as a module: `.castflow/core/rules/module-catalog.md`. Skill bodies live in `.castflow-runtime/skills/` and are projected to `.claude/skills` and `.agents/skills`. Grok and Cursor scan those paths; do not copy into `.grok/skills` or `.cursor/skills`.

## Yield

- Pasted `/goal` scan prompt -> follow `MODULE_SKILL_LOOP_ENGINE_SYSTEM_PROMPT.md` (programmer-* only; one at a time)
- GUI JSON queue / `castflow generate skills` (architect / debug / profiler) -> **skill-creator**, one then stop
- Distilling traces into rules -> **origin-evolve-skill**
- Implementing a feature in a module -> that module's **programmer-*-skill**

## Flow

1. Tell the user to run `CastFlow\castflow.bat` (or `python .castflow/manager.py launch`). The bat prints the 4-step guide. Do **not** ask language here, do **not** run seed yourself.
2. Unchecked box: 开启冷启动 only copies framework skills and core files. There is no AI prompt. Stop.
3. Checked box: user may edit the prompt (empty = `/goal` read and follow `.castflow-runtime/skills/MODULE_SKILL_LOOP_ENGINE_SYSTEM_PROMPT.md`). After they paste it here, read that file and follow it. `/goal` starts the long task; the file has the rest. Do not also drain the GUI JSON queue in the same turn. Do not launch parallel generate subagents.

If they paste `/goal` plus that path: read the file and follow it. Do not refuse because there is no `Assets/Scripts`, no `.cs`, or fewer than 3 files per folder.

Fallback if they cannot open the GUI: `python .castflow/manager.py setup` then `python .castflow/manager.py ui`. To start over: GUI 回退并重新冷启动, or `python .castflow/manager.py unseed`.

## Do not

- Run seed/unseed yourself unless the user cannot open the GUI
- Write skill bodies into `.claude/skills` or other mirrors
- Treat "no .cs files" or "no Scripts folder" as a reason to skip the scan the user asked for
- Scan CastFlow / `.castflow` / `.castflow-runtime` / adapter trees, or list them as module options
- Run `bootstrap.py --skill` (removed)

## Nav

| Need | File |
|------|------|
| Dialogue samples | EXAMPLES.md |
| Hard rules | SKILL_MEMORY.md |
| Module contract | `.castflow/core/rules/module-catalog.md` |
| Scan/select/generate flow | `MODULE_SKILL_LOOP_ENGINE_SYSTEM_PROMPT.md` |
| Generate path | loop-engine `/goal` (programmer-*); JSON queue one-then-stop (architect/debug/profiler) |
