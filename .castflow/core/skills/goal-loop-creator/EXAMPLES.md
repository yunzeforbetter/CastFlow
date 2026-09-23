# Goal Loop Creator Examples

These examples are the smallest useful interaction and package shape. They are scenarios for this skill, not instructions to invoke a host command.

## Quick navigation

| Scenario | Use when | Main result |
|----------|----------|-------------|
| 1. New package from an open brief | The user has a goal, but important boundaries are unknown | A clarified ledger and a ready or draft package |
| 2. Revise an existing package | The objective or the project has changed | A new revision and run, without corrupting the active run |
| 3. Asset and host handoff | The task depends on documents, images, or host capabilities | An asset manifest and honest invocation instructions |
| 4. Blocked package | A required decision or capability is unavailable | A persisted blocker and one recovery question |
| 5. Existing package | `RUN_PROMPT.md` is already present | Yield to the package runner. Do not rebuild |
| 6. One-pass system versus a skeleton | Choosing the generated package shape | A dense work order. Never a phase-gated halt |
| 7. Thin brief, through to mastery | Documents or data are thin or unclear | A question sequence, persisted opens, `DRAFT` until answered |

## Scenario 1: New package from an open brief

**User intent**: turn a broad request such as "prepare a repeatable migration workflow" into a long-running loop.

Start by showing the extracted objective, the expected artifacts, the assumed inputs, and the open decisions. Ask only questions that could change the target, the allowed side effects, acceptance, ownership, or an edge handling. At most three per turn, then continue across turns until document and data opens are mastered. A useful first batch is:

1. What is the final artifact, and who accepts it?
2. Which paths or systems may change, and which are forbidden?
3. What evidence proves completion, and which edges must have a handling?

After the answers, persist what is confirmed and what stays `open`, with an owner. Create atomic requirement rows. If a mandatory row is still open, emit a `DRAFT` and keep asking. Never fill the gap with a plausible rule.

This skill writes `RUN_PROMPT.md` as one compact work order for the named system: role and done bar, known entries labeled `pending project confirmation` where unverified, must-read, a bounded execution protocol, behavior once, hard constraints, edges and handling, numbered acceptance covering those edges, non-goals, and a dialogue-only final reply. Dense sections for the named system are necessary. Do not paste another skill file, an enum dump, or a protocol catalog. Do not instruct a one-phase-then-halt skeleton.

**Project reference**: `.castflow/core/skills/goal-loop-creator/SKILL.md`

**Traps**:

- Asking a preference question that cannot change the target
- Treating a written prompt as `DONE` for the eventual task
- Emitting a phase-gated skeleton (one phase, then halt, gap list as DONE)
- Using a thin feature list, or happy-path-only acceptance, as the quality bar

See [SKILL_MEMORY.md](SKILL_MEMORY.md) Rule 1, Rule 4, and Rule 7.

## Scenario 2: Revise an existing package

**User intent**: add an output, or change the target project, after a run has already started.

Read `MANIFEST.yaml`, `state/CURRENT_RUN`, and the current run state. Compare the normalized goal, scope, host profile, and project snapshot. If any of those changed materially, copy the confirmed specification into a new package revision, create a new run id, and mark downstream artifacts stale. Keep the old run and its accepted artifacts for audit and rollback. If only a non-semantic note changed, update the note and do not reset quality budgets.

**Project reference**: `.castflow/core/skills/goal-loop-creator/SKILL.md`

## Scenario 3: Asset and host handoff

**User intent**: supply design documents, reference images, or a data file to a loop that will run through `/goal`.

Record each asset in `ASSETS.yaml` with its relative path, purpose, source type, sensitivity, and integrity value. Labeled UI screenshots and state sheets are required must-read paths in `RUN_PROMPT.md`. Put only short pointers in `CONTEXT.md`. Keep binaries out of the prompt. The manifest says whether the host can read documents, inspect images, execute commands, and persist state. If a required image or vision capability is absent, the handoff says `BLOCKED` or `design-unverified`. It never says "missing does not block" for a UI state sheet, and it never claims the host performed a check it could not perform.

**Project reference**: `.castflow/core/skills/goal-loop-creator/SKILL.md`

## Scenario 4: Blocked package

**User intent**: continue despite a missing decision, a failed gate, or an unavailable filesystem.

Write the blocker into builder or run state with its phase, the affected requirements, the evidence already tried, and one recovery question the user can act on. Do not reset a quality-failure budget by rewriting the wording. Separate a missing user decision from an infrastructure failure. Resume only after the matching state and input fingerprint are updated.

**Project reference**: `.castflow/core/skills/goal-loop-creator/SKILL.md`

## Scenario 5: Existing package

**User intent**: run or resume a package that already has `RUN_PROMPT.md`.

Do not rebuild. Point the user at `HANDOFF.md` and the current run pointer. Creating a module skill from a pasted `/goal` scan prompt follows `MODULE_MARK_SYSTEM_PROMPT.md`, not this skill. `castflow generate skills` is **skill-creator**.

**Project reference**: `.castflow/core/skills/skill-creator/SKILL.md`

## Scenario 6: One-pass system versus a skeleton

**User intent**: generate a loop that must finish a named system, not a recoverable phase machine.

Do not emit a phase-gated skeleton: "execute exactly one `WORKFLOW.yaml` phase," `task DONE` allowed without a playable loop, `GAPS.md` as a mandatory success path, Recover always-reading GOAL, REQUIREMENTS, ACCEPTANCE, and CONTEXT, or screenshots marked optional with "missing does not block."

Emit a one-pass work order, and interview until mastery, with edges and handling: one dense `RUN_PROMPT.md` with role and done bar, known entries as `pending project confirmation` where unverified, bounded explore then implement, behavior once, hard constraints, each edge with a handling, numbered acceptance covering those edges, non-goals, and a dialogue-only final reply. Point at the required labeled screens. A thin feature list is a seed, not the quality bar.

**Project reference**: `.castflow/core/skills/goal-loop-creator/SKILL.md`

**Traps**:

- Cloning requirements and acceptance 1:1, plus an enum dump in `CONTEXT.md`
- Stopping after one phase while the named system is still unimplemented
- Treating a one-line brief as the quality bar

See [SKILL_MEMORY.md](SKILL_MEMORY.md) Rule 7 and Pitfall 6.

## Scenario 7: Thin brief, through to mastery

**User intent**: "create this activity," plus a thin feature list. Tables, protocols, prefab paths, ids, and screenshot files are unnamed.

Do not guess those facts. First turn: at most three questions (identity, the protocol or an explicit none, and the required UI image paths). Persist answers as `confirmed`. Persist the rest as `open`, with an owner. Later turns: the remaining product edges and their handling, if the brief is silent. Stop asking only when every material open is confirmed or explicitly owned. Emit `DRAFT` or `WAIT_HUMAN` while opens remain. The work order still lists edges and handling (empty slots, a full grid, expired, skip-anim, item-lack, a missing protocol, stale async, close-without-commit) so the runner does not invent them.

**Project reference**: `.castflow/core/skills/goal-loop-creator/SKILL.md`

**Traps**:

- One question batch, then PACKAGE with assumed APIs
- Inventing protocol names so the package looks `READY`
- Happy-path acceptance only (open the window, click draw)

See [SKILL_MEMORY.md](SKILL_MEMORY.md) Rule 4 and Pitfall 7.

## Package review

Before handoff, review the package the way a user would:

- Can a fresh runner find the package root from `HANDOFF.md`?
- Does `RUN_PROMPT.md` contain the one-pass sections (role and done bar, known entries, must-read, execution protocol, behavior, hard constraints, edges and handling, acceptance, non-goals, final reply)?
- Do acceptance scenes cover those edges, not only the happy path?
- Are remaining document and data opens persisted, not guessed?
- Are write targets, non-goals, and rollback limits unambiguous?
- Do required images have a real must-read path, not an optional stand-in?
- Is the always-read bundle free of enum, protocol, and skill-body dumps?
- Does the package stop instead of guessing when a required fact is missing?
- Was `RUN_PROMPT.md` authored here, not copied from another skill?
- Would a runner be told that DONE is allowed without the named system? If yes, reject the package.

A `READY` package is a resumable one-pass work order. It is not the finished task. Runner `DONE` still requires delivering the named system.
