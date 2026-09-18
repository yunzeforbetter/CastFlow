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

## Scenario 1: New package from an open brief

**User intent**: Turn a broad request such as "prepare a repeatable migration
workflow" into a long-running loop.

Start by showing the extracted objective, expected artifacts, assumed inputs,
and open decisions. Ask only questions that could change the target, allowed
side effects, acceptance, or ownership. A useful first batch is:

1. What is the final artifact and who accepts it?
2. Which paths or systems may be changed, and which are forbidden?
3. What evidence proves completion, and what must remain manual?

After the answers, create atomic requirement rows. Each row has an identifier,
statement, priority, status, source, and linked acceptance identifiers. If a
mandatory row remains open, produce a draft and stop at the human gate instead
of filling the gap with a plausible rule.

This Skill writes `RUN_PROMPT.md` as a short execution contract: recover from
package state, do one work unit, verify against `ACCEPTANCE.yaml`, checkpoint,
stop on `WAIT_HUMAN` / `BLOCKED` / `DONE`. Put phase detail in `WORKFLOW.yaml`
or `GOAL.md` if needed. Do not paste another skill file into the runner prompt.
The package slug and root belong in `MANIFEST.yaml` before handoff.

**Project reference**: `.castflow/core/skills/goal-loop-creator/SKILL.md`

**Traps**:
- Asking preference questions that cannot change the target
- Treating a written prompt as `DONE` for the eventual task

See [SKILL_MEMORY.md](SKILL_MEMORY.md) Rule 1 and Rule 4.

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

Record each asset in `ASSETS.yaml` with its relative path, purpose, required
phase, source type, sensitivity, and integrity value. Put summaries in
`CONTEXT.md`; keep large binaries out of `RUN_PROMPT.md`. The manifest lists
whether the host can read documents, inspect images, execute commands, and
persist state. If a required capability is absent, the handoff says
`BLOCKED` or requests a user-provided substitute. It never claims that a host
performed a check it could not perform.

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
Creating a module skill from a pasted `/goal` scan prompt is **bootstrap-skill**
(loop engine), not this Skill. `castflow generate skills` for architect/debug/
profiler is **skill-creator**, one then stop.

**Project reference**: `.castflow/core/skills/skill-creator/SKILL.md`

## Package review checklist

Before handoff, review the package as a user would:

- Can a fresh runner find the package root from `HANDOFF.md`?
- Does `RUN_PROMPT.md` name the canonical state and the next action?
- Are all mandatory requirements linked to observable acceptance checks?
- Are write targets, non-goals, and rollback limits unambiguous?
- Do optional assets have a clear purpose and a graceful fallback?
- Does the package stop instead of guessing when a required fact is missing?
- Was `RUN_PROMPT.md` authored here, not copied from another skill?

A READY package is a resumable work order. It is not the finished task.
