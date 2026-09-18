# Goal Loop Creator Examples

These examples describe the smallest useful interaction and package shape.
They are scenarios for this Skill, not instructions to invoke a host command.

## Quick navigation

| Scenario | Use when | Main result |
|----------|----------|-------------|
| 1. New package from an open brief | The user has a goal but important boundaries are unknown | A clarified ledger and a ready or draft package |
| 2. Revise an existing package | The objective or project has changed | A new revision and run without corrupting the active run |
| 3. Asset and host handoff | The task depends on documents, images, or host capabilities | An asset manifest and honest invocation instructions |
| 4. Blocked package | A required decision or capability is unavailable | A persisted blocker and a precise recovery question |
| 5. Existing package | A `RUN_PROMPT.md` is already present | Yield to the package runner; do not rebuild |
| 6. One-pass 系统功能 vs skeleton | Deciding generated package shape | Dense work order; never a phase-gated halt |
| 7. Incomplete brief to mastery | Docs/data are thin or unclear | Question sequence, opens persist, DRAFT until answered |

## Scenario 1: New package from an open brief

**User intent**: Turn a broad request such as "prepare a repeatable migration
workflow" into a long-running loop.

Start by showing the extracted objective, expected artifacts, assumed inputs,
and open decisions. Ask only questions that could change the target, allowed
side effects, acceptance, ownership, or a 边界处理方案. At most three per
turn, then continue across turns until document/data opens are mastered.
A useful first batch is:

1. What is the final artifact and who accepts it?
2. Which paths or systems may be changed, and which are forbidden?
3. What evidence proves completion, and which 边界 must have a 处理方案?

After the answers, persist confirmed vs `open` with an owner. Create atomic
requirement rows. If a mandatory row remains open, produce a `DRAFT` and
keep asking; never fill the gap with a plausible rule.

This Skill writes `RUN_PROMPT.md` as a compact one-pass 系统功能 work order:
role + 完成标准, 已知入口 labeled 待项目确认, 必读, bounded 执行协议, 功能
once, 硬约束, 边界与处理方案, numbered 验收 covering those 边界, 非目标,
dialogue-only 最终回复. Dense 系统功能 sections are necessary. Do not paste
another skill file, an enum dump, or a protocol catalog. Do not instruct a
one-phase-then-halt skeleton.

**Project reference**: `.castflow/core/skills/goal-loop-creator/SKILL.md`

**Traps**:
- Asking preference questions that cannot change the target
- Treating a written prompt as `DONE` for the eventual task
- Emitting a phase-gated skeleton (one phase then halt, gap list as DONE)
- Using a thin feature list or happy-path-only 验收 as the quality bar

See [SKILL_MEMORY.md](SKILL_MEMORY.md) Rule 1, Rule 4, and Rule 7.

## Scenario 2: Revise an existing package

**User intent**: Add a new output or change the target project after a run has
already started.

Read `MANIFEST.yaml`, `state/CURRENT_RUN`, and the current run state. Compare
the normalized goal, scope, host profile, and project snapshot. If any of those
changed materially, copy the confirmed specification into a new package
revision, create a new run identifier, and mark downstream artifacts stale.
Keep the old run and its accepted artifacts for audit and rollback. If only a
non-semantic note changed, update the note without resetting quality budgets.

**Project reference**: `.castflow/core/skills/goal-loop-creator/SKILL.md`

## Scenario 3: Asset and host handoff

**User intent**: Supply design documents, reference images, or a data file to a
loop that will run through `/goal`.

Record each asset in `ASSETS.yaml` with its relative path, purpose, source
type, sensitivity, and integrity value. Labeled UI screenshots and state
sheets are required 必读 paths in `RUN_PROMPT.md`. Put only short pointers
in `CONTEXT.md`; keep binaries out of the prompt. The manifest lists whether
the host can read documents, inspect images, execute commands, and persist
state. If a required image or vision capability is absent, the handoff says
`BLOCKED` or `设计稿未验证`. It never says "missing does not block" for a
UI state sheet, and it never claims that a host performed a check it could
not perform.

**Project reference**: `.castflow/core/skills/goal-loop-creator/SKILL.md`

## Scenario 4: Blocked package

**User intent**: Continue despite a missing decision, a failed gate, or an
unavailable filesystem.

Write the blocker to the builder or run state with its phase, affected
requirements, attempted evidence, and one actionable recovery question. Do not
reset a quality-failure budget by rewriting the wording. Separate a missing
user decision from an infrastructure failure, and resume only after the
corresponding state and input fingerprint are updated.

**Project reference**: `.castflow/core/skills/goal-loop-creator/SKILL.md`

## Scenario 5: Existing package

**User intent**: Run or resume a package that already has `RUN_PROMPT.md`.

Do not rebuild. Point the user at `HANDOFF.md` and the current run pointer.
Creating a module skill from a pasted `/goal` scan prompt follows
`MODULE_SKILL_LOOP_ENGINE_SYSTEM_PROMPT.md`, not this Skill.
`castflow generate skills` is **skill-creator**.

**Project reference**: `.castflow/core/skills/skill-creator/SKILL.md`

## Scenario 6: One-pass 系统功能 vs skeleton

**User intent**: Generate a loop that must finish a named system, not a
recoverable phase machine.

Do not emit a phase-gated skeleton: `Execute exactly one WORKFLOW.yaml phase`,
`task DONE` allowed without a playable loop, `GAPS.md` as a mandatory success
path, Recover always-reads GOAL/REQUIREMENTS/ACCEPTANCE/CONTEXT, screenshots
marked optional with "missing does not block".

Emit a one-pass work order **plus** interview-until-mastery and
边界与处理方案: one dense `RUN_PROMPT.md` with role + 完成标准, 已知入口
as 待项目确认, bounded explore then implement, 功能 once, 硬约束, each
边界 with a 处理方案, numbered 验收 covering those edges, 非目标,
dialogue-only 最终回复. Point at required labeled screens. A thin feature
list is a seed, not the quality bar.

**Project reference**: `.castflow/core/skills/goal-loop-creator/SKILL.md`

**Traps**:
- Cloning REQ/ACC 1:1 plus an enum dump in `CONTEXT.md`
- Stopping after one phase when the named system is still unimplemented
- Treating a one-line brief as the quality bar

See [SKILL_MEMORY.md](SKILL_MEMORY.md) Rule 7 and Pitfall 6.

## Scenario 7: Incomplete brief to mastery

**User intent**: "Create this activity" plus a thin feature list. Tables,
protocols, prefab paths, ids, and screenshot files are unnamed.

Do not guess those facts. First turn: at most three questions (identity,
protocol or confirm none, required UI image paths). Persist answers as
`confirmed`; persist the rest as `open` with owner. Next turns: remaining
product edges and 处理方案 if the brief is silent. Stop asking only when
every material open is confirmed or explicitly owned. Emit `DRAFT` /
`WAIT_HUMAN` while opens remain. The work order still lists 边界与处理方案
(empty slots, full grid, expired, skip-anim, item-lack, missing protocol,
stale async, close-without-commit) so the runner does not invent them.

**Project reference**: `.castflow/core/skills/goal-loop-creator/SKILL.md`

**Traps**:
- One question batch, then PACKAGE with assumed APIs
- Inventing protocol names so the package looks `READY`
- Happy-path 验收 only (open window, click draw)

See [SKILL_MEMORY.md](SKILL_MEMORY.md) Rule 4 and Pitfall 7.

## Package review checklist

Before handoff, review the package as a user would:

- Can a fresh runner find the package root from `HANDOFF.md`?
- Does `RUN_PROMPT.md` contain the one-pass work-order sections (role,
  完成标准, 已知入口, 必读, 执行协议, 功能, 硬约束, 边界与处理方案, 验收,
  非目标, 最终回复)?
- Are 验收场景 covering those 边界, not happy-path only?
- Are remaining document/data opens persisted (not guessed)?
- Are write targets, non-goals, and rollback limits unambiguous?
- Do required images have a real 必读 path (not optional OSS)?
- Is the always-read bundle free of enum/protocol/skill-body dumps?
- Does the package stop instead of guessing when a required fact is missing?
- Was `RUN_PROMPT.md` authored here, not copied from another skill?
- Would a runner be told that DONE is allowed without the named system? If
  yes, reject the package.

A READY package is a resumable one-pass work order. It is not the finished
task, but runner `DONE` still requires delivering the named 系统功能.
