# Project Rules (CastFlow)

This file is generated from CastFlow (`ROOT_RULES.template.md`). Harness section is above the boundary; edit only the project section below it.

Skill source of truth: `.castflow-runtime/skills/` (never edit adapter mirrors).

## Using skills (T1-T4)

Host auto-injects this file and the matched skill `SKILL.md`.

| Moment | When | Read |
|--------|------|------|
| T1-PREPARE | Before writing code | whole `GLOBAL_SKILL_MEMORY.md` + target `SKILL_MEMORY.md` + EXAMPLES as needed |
| T2-EXECUTE | While writing | no extra file; apply protocol 3 from the T1 load |
| T3-FEEDBACK | User accepts/rejects | `protocols/validated-protocol.md` |
| T4-MAINTAIN | Creating/editing a skill | `SKILL_ITERATION.md` + that skill's `ITERATION_GUIDE.md` |

## CastFlow commands

- Pasted `/goal` scan prompt — follow `MODULE_SKILL_LOOP_ENGINE_SYSTEM_PROMPT.md`: land `_skill-gen-queue/`, one programmer skill at a time, mark done, compact, delete the queue. No parallel generate subagents.
- `castflow generate skills` — JSON queue for architect/debug/profiler only: write one, then stop. Do not mix with the `/goal` loop in the same turn.
- `castflow.bat` / `python .castflow/manager.py launch` — GUI cold start (config + seed) and visual console.
- `python .castflow/manager.py ui` — visual console (skills, evolution, adapters, queue).
- `python .castflow/manager.py sync` — project runtime skills to `.claude/skills` and `.agents/skills` (Grok/Cursor scan those; no extra skill trees).

<!-- if:evolution -->
## Experience capture (evolution plugin ON)

On rework, correction, or a hard constraint, write a markdown file under `.castflow-runtime/memory/` with YAML `name`, `type: feedback` (or `project` / `reference`), and `description`. Do not write personal `type: user` notes there. Do not write team rules into host Memory directories.

Daily sessions must not Read `.castflow-runtime/traces/trace.md` or `.castflow-runtime/memory/`. Reminders may Read `.castflow-runtime/traces/.unflushed` and `.evolve_nudge` only.

Then run `python .castflow/manager.py flush` if your host has no Stop hook (Codex). Distill later with `origin evolve`. Never edit `.castflow-runtime/traces/trace.md` by hand.

If `.unflushed` exists, suggest `python .castflow/manager.py flush` then `origin evolve`. If only `.evolve_nudge` exists, suggest `origin evolve`.
<!-- endif:evolution -->

<!-- if:no-evolution -->
## Experience capture (evolution plugin OFF)

The CastFlow evolution plugin is disabled. Do not write `.castflow-runtime/memory/`, do not run origin-evolve, do not install trace hooks.
<!-- endif:no-evolution -->

## API hallucination (P0)

Do not invent project APIs. Evidence is EXAMPLES, an opened definition, or a user pointer. Unverified calls get TODO; do not guess signatures. Details: `GLOBAL_SKILL_MEMORY.md` protocol 1.

<!-- ========== project section (team-owned) ========== -->

## Code naming

Follow existing code in this repository. Add team conventions below.
