# Goal Loop Creator Iteration Guide

## Positioning

This skill is CastFlow's long-task converter. It compiles a requirement the user has aligned into a resumable Goal Loop Package that an external runner can execute. The loop-engine idea is one pass over the named system, not a phase-gated skeleton. The builder interviews unclear documents and data until mastery, and it encodes a handling for each edge. It does not replace the external goal runner, skill-creator, or a host scheduler. It authors `RUN_PROMPT.md`. It does not wrap another skill.

## Iteration rules

### Rule 1: Change behavior only with a concrete trigger

Trigger: users report that alignment, package creation, handoff, or recovery produces a wrong result.

Priority: high.

File: `SKILL.md` for workflow or routing; `SKILL_MEMORY.md` for a recurring non-negotiable constraint; `EXAMPLES.md` for a representative usage.

Checks:

- Name the failing stage and its source of truth.
- Add a narrow rule or example. Do not repeat the whole workflow.
- Keep the builder and the runner apart.

### Rule 2: Add a package field only when it closes a verified gap

Trigger: a real package cannot express a requirement, boundary, host capability, asset, acceptance check, or recovery fact.

Priority: high.

File: `SKILL.md` describes what the field is for. `EXAMPLES.md` shows it. `SKILL_MEMORY.md` gets a rule only when leaving the field out would cause a repeatable failure.

Checks:

- Say whether the field is mandatory or optional.
- Define its owner, allowed values, and effect on readiness.
- Add one scenario showing how a runner uses it.
- Check that the field does not duplicate an existing source of truth.

### Rule 3: Keep host support based on capabilities

Trigger: a host gains or loses persistence, subagents, command execution, filesystem access, vision, or scheduling.

Priority: medium.

File: `SKILL.md` for the user-facing boundary; `SKILL_MEMORY.md` for the truthfulness rule; `EXAMPLES.md` for a handoff or fallback.

Checks:

- Describe capabilities you can observe, not an undocumented product promise.
- Keep `/goal` invocation text in the handoff, not inside the runner logic.
- Give a serial or manual fallback when that is safe. Otherwise block.

### Rule 4: Keep runner-facing text dense

Trigger: the always-read bundle dumps enums, protocols, skill bodies, or schema copies, or it clones REQUIREMENTS and ACCEPTANCE 1:1; or the package tells the runner to halt after one phase without delivering the named system.

Priority: high.

File: `SKILL.md` for work-order sections and load policy; `EXAMPLES.md` for a good package shape against a bad one; `SKILL_MEMORY.md` for Rule 7, Pitfall 2, and Pitfall 6.

Checks:

- `RUN_PROMPT.md` is the only always-read contract. Satellites load on demand.
- Do not refill context by moving dumps into always-read GOAL, CONTEXT, or YAML.
- Required images have a must-read path. Missing is a blocker, not an optional asset.
- Do not emit a phase-gated skeleton.
- Do not import another skill file as the runner prompt.
- A thin feature list is a seed, not the quality bar.

## File responsibilities

| File | Edit when | Do not put here |
|------|-----------|-----------------|
| `SKILL.md` | Trigger, scope, workflow, or the package contract changes | Long examples, history, or the full hard-rule catalog |
| `EXAMPLES.md` | A common package scenario or fallback becomes clearer | New mandatory rules, dates, or release notes |
| `SKILL_MEMORY.md` | A repeatable constraint or trap is found | Progress logs, dates, version history, or speculative advice |
| `ITERATION_GUIDE.md` | The maintenance process or a quality measure changes | Run results, user names, or a diary |

## Quality measures

1. Alignment: no mandatory requirement is `open` when a package is reported `READY`.
2. References: every mandatory package path and cross-file link resolves from the package root.
3. Acceptance: every mandatory requirement has at least one observable check and an evidence location.
4. Recovery: a fresh invocation can name the current run, package revision, phase, status, and next action without chat history.
5. Host honesty: the package never claims a capability the host lacks, or a check that was not performed.
6. Independence: this skill authored `RUN_PROMPT.md`.
7. One-pass delivery: runner `DONE` requires the named system with evidence. A gap list is not success.
8. Density: always-read text leaves room for code. No architecture dumps. Required labeled screens are must-read.
9. Interview: unclear documents and data stay `open` until answered. The builder keeps asking across turns. `READY` stays blocked while they remain.
10. Edges: every listed edge has a handling and a matching acceptance scene. Happy-path-only acceptance fails.

## Maintenance

Read this guide and the current four files before editing. Make the smallest change that fixes the observed gap. Keep each statement in the file that owns it. Check navigation links. The directory must still contain exactly the four required Markdown files. Recheck frontmatter, prohibited symbols, file duties, and the quality measures before handing the revision back.
