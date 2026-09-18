# Goal Loop Creator Iteration Guide

## Quick navigation

| Need | Section |
|------|---------|
| What this Skill owns | Positioning |
| When to change a file | Iteration rules |
| Which file receives a change | File responsibilities |
| How to verify a revision | Quality measures |

## Positioning

This Skill is CastFlow's **long-task conversion system**. It compiles
user-aligned requirements into a resumable Goal Loop Package that an
external runner can execute under loop-engine ideas: one-pass 系统功能,
not a phase-gated skeleton. The builder interviews unclear docs and data
until mastery and encodes 边界处理. It does not replace the external goal
runner, skill-creator, or a host scheduler. It authors `RUN_PROMPT.md`
and does not wrap another skill.

## Iteration rules

### Rule 1: Change behavior only with a concrete trigger

Trigger: users report that alignment, package creation, handoff, or recovery
produces an incorrect result.

Priority: High.

File: `SKILL.md` for workflow or routing; `SKILL_MEMORY.md` for a recurring
non-negotiable constraint; `EXAMPLES.md` for a representative usage pattern.

Checks:

- Identify the failing stage and its source of truth.
- Add a narrow rule or example instead of repeating the whole workflow.
- Preserve the builder and runner boundary.

### Rule 2: Add a package field only when it closes a verified gap

Trigger: a real package cannot express a requirement, boundary, host capability,
asset, acceptance check, or recovery fact.

Priority: High.

File: `SKILL.md` describes the field's purpose; `EXAMPLES.md` shows it.
`SKILL_MEMORY.md` receives a rule only when omission would create a repeatable
failure.

Checks:

- State whether the field is mandatory or optional.
- Define its owner, allowed values, and readiness effect.
- Add one scenario showing how a runner uses it.
- Verify that the field does not duplicate an existing source of truth.

### Rule 3: Keep host support capability-based

Trigger: a host adds or loses persistence, subagents, command execution,
filesystem, vision, or scheduling behavior.

Priority: Medium.

File: `SKILL.md` for the user-facing boundary; `SKILL_MEMORY.md` for the
truthfulness rule; `EXAMPLES.md` for a handoff or fallback scenario.

Checks:

- Describe observable capabilities, not undocumented product promises.
- Keep `/goal` invocation text in the handoff, not in the runner logic.
- Provide a serial or manual fallback when it is safe; otherwise block.

### Rule 4: Keep generated runner-facing text dense

Trigger: the always-read bundle dumps enums, protocols, skill bodies, schema
copies, or 1:1 REQUIREMENTS/ACCEPTANCE clones; or the package tells the
runner to halt after one phase without delivering the named 系统功能.

Priority: High.

File: `SKILL.md` for work-order sections and load policy; `EXAMPLES.md` for
good-vs-bad package shape; `SKILL_MEMORY.md` for Rule 7, Pitfall 2, and
Pitfall 6.

Checks:

- `RUN_PROMPT.md` is the only always-read contract; satellites load on demand.
- Do not refill context by moving dumps into always-read GOAL/CONTEXT/YAML.
- Required images have a 必读 path; missing is a blocker, not optional OSS.
- Do not emit a phase-gated skeleton.
- Do not import another skill file as the runner prompt.
- A thin feature list is a seed, not the quality bar.

## File responsibilities

| File | Edit when | Do not put here |
|------|-----------|-----------------|
| `SKILL.md` | Trigger, scope, workflow, or package contract changes | Long examples, history, or detailed hard-rule catalog |
| `EXAMPLES.md` | A common package scenario or fallback becomes clearer | New mandatory rules, dates, or release notes |
| `SKILL_MEMORY.md` | A repeatable constraint or trap is discovered | Progress logs, dates, version history, or speculative advice |
| `ITERATION_GUIDE.md` | The maintenance process or quality measures change | Run results, user names, or historical diary entries |

## Quality measures

1. Alignment readiness: no mandatory requirement is `open` when a package is
   reported `READY`.
2. Reference integrity: every mandatory package path and cross-file link
   resolves from the package root.
3. Acceptance coverage: every mandatory requirement has at least one
   observable acceptance check and an evidence location.
4. Recovery clarity: a fresh invocation can identify the current run, package
   revision, phase, status, and next action without chat history.
5. Host honesty: the package never claims an unavailable capability or an
   unperformed check.
6. Independence: `RUN_PROMPT.md` is authored by this Skill.
7. One-pass delivery: runner `DONE` requires the named 系统功能 with
   evidence; a gap list is not success.
8. Density: always-read text leaves model capacity for code; no architecture
   dumps. Required labeled screens are must-read.
9. Interview mastery: unclear docs/data stay `open` until answered; the
   builder keeps asking across turns; `READY` is blocked while they remain.
10. 边界 coverage: every listed edge has a 处理方案 and a matching 验收
    scene; happy-path-only 验收 fails.

## Maintenance procedure

Read this guide and the current four files before editing. Make the smallest
change that fixes the observed gap, keep each statement in its owning file,
check all navigation links, and inspect the final directory for exactly the
four required Markdown files. Recheck frontmatter, prohibited symbols, file
responsibilities, and the quality measures before handing the revision back to
the parent maintainer.
