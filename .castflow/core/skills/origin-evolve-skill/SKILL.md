---
name: origin-evolve-skill
description: trace.md 执行记录进化：处理 trace 模式归纳、proposal 生成、知识更新审批与 skill 规则沉淀。
---

# Origin Evolve

Mission: turn `.claude/traces/trace.md` into approved updates of `.skillmanager/.skills/` (never write skill source files under `.claude/skills/` mirrors).

Trigger: user input `origin evolve` (or equivalent intent).

## Quick Navigation

| Need | See |
|------|-----|
| Full proposal examples | EXAMPLES.md |
| Evidence requirements (Rule 1) | SKILL_MEMORY.md#rule-1-evidence-based-proposals |
| Attribution decision tree (Rule 2) | SKILL_MEMORY.md#rule-2-attribution-decision-tree |
| Append / Merge / Retire operations (Rule 3) | SKILL_MEMORY.md#rule-3-append--merge--retire |
| User approval policy (Rule 4) | SKILL_MEMORY.md#rule-4-user-approval-required-for-every-write |
| Format & capacity compliance (Rule 5) | SKILL_MEMORY.md#rule-5-format--capacity-compliance |
| Common pitfalls | SKILL_MEMORY.md#pitfalls |
| When to update this skill | ITERATION_GUIDE.md |

## Trace Fields (schema:4)

The scoring/buffer subsystem and the hand-written IDP path were **retired**. A trace entry is now written ONLY when the model wrote auto-memory during the session — a memory-snapshot ledger record. Pure code sessions produce no trace entry.

Hook-generated fields: `timestamp`, `type`, `validated`, `pipeline_run_id`, `memory_snapshots`.

Lifecycle: `status` (pending/processed/expired/invalid), `validated` (`_`/true/false/pending-pipeline/invalid).

**Memory snapshots are the sole learning source.** `memory_snapshots: <N>` counts embedded `<!-- MEMORY slug:… type:… -->…<!-- /MEMORY -->` subblocks — verbatim copies of Claude Code auto-memory files the model wrote (`type` is `feedback`/`project`/`reference`; personal `user` memories are filtered out before capture). `type:` on the TRACE line is the dominant snapshot type (feedback > project > reference). These are **raw material, not conclusions**: distilling them into rules is your job in Step 2/3. Treat `feedback` content as the strongest evidence (an explicit rule the user gave), and always verify a snapshot's claim against current code/skills before proposing (snapshots are point-in-time copies and may have drifted).

**Retired fields (legacy entries only)**: `score`, `score_breakdown`, `modules`, `correction`, `mode`, `skills`, `error_cause`, `fix_approach`, `user_feedback`, `lesson`. schema:1-3 entries may still carry these; read them if present but do not expect or require them on schema:4.

## Execution Flow

```
Step 1 Read & Triage -> Step 2 Identify Patterns -> Step 3 Generate Proposals -> Step 4 User Approval -> Step 5 Write & Mark Processed -> Step 6 Calibrate (optional)
```

### Step 1: Read & Triage

Acquire `.trace_lock` (overwrite if stale). Apply lifecycle transitions: `pending` with stale validated -> `expired`; `pending-pipeline` past expiry -> `invalid`.

**Schema version gate**: the current trace schema is `4`. Entries without a schema tag are treated as schema 1 (legacy). schema:1-3 entries may carry now-retired fields (`score`/`modules`/`correction`/experience fields); read them if present but never require them. Accept `schema:1` through `schema:4`. If any entry has `schema:N` where N > 4, abort and report "Unsupported trace schema version N. Update origin-evolve."

Read trace.md, keep `pending` only, then exclude entries with `validated:pending-pipeline` from proposal candidates until they are finalized to `true` / `false` or expire to `invalid`. Since schema:4 entries only exist because the model captured memory, treat **any entry with a `feedback` memory snapshot as sufficient evidence to act on** — do not gate it behind a minimum count. If no pending entry carries a memory snapshot (and no legacy correction signal exists), suggest waiting.

Compute three diagnostic counts across `.skillmanager/.skills/*/SKILL_MEMORY.md` and include in the analysis summary:
- within-skill rule pairs with anchor Jaccard >= 0.5
- cross-skill identical anchor sets
- cross-skill rule pairs with anchor Jaccard >= 0.5

Non-zero counts indicate prior attribution or merge errors and should inform Step 2 proposal generation.

Sort priority:
- Exclude `validated:pending-pipeline` from the priority queue; they are runtime-in-flight, not proposal evidence.
- P0: `validated:false` (a rejected pipeline result — something went wrong, highest signal)
- P1: any entry carrying a `feedback`-type memory snapshot (an explicit user rule — high-confidence raw material)
- P2: `validated:true` + memory snapshot (validated context worth distilling)
- P3: `memory_snapshots >= 1` with `project`/`reference` snapshots only
- P4 (legacy): schema:1-3 entries with a `correction` signal, by recency

### Step 2: Identify Patterns

**Memory-snapshot distillation is the primary (and now essentially only) learning path.** For each entry with `memory_snapshots >= 1`, read the `<!-- MEMORY -->` subblock content and distill it into a candidate rule yourself — the snapshot IS the raw material. Per snapshot:
- `feedback` type → the content is already a rule the user gave ("X 场景必须用 Y" + why). Treat it as a **single-trace-sufficient** signal: one feedback snapshot can justify a proposal, because it is an explicit user directive, not an inferred pattern. Distill it into the target skill's `SKILL_MEMORY.md` (single-skill) or `GLOBAL_SKILL_MEMORY.md` (cross-skill), following existing rule format (rule + Why + How to apply).
- `project` type → context/decision. Use to inform proposals, rarely a rule on its own.
- `reference` type → external-resource pointer. Route to the relevant skill's reference notes if durable.
- **Always verify before proposing**: a snapshot is a point-in-time copy. Confirm any file path / API / flag it names still exists (grep/read current code) before turning it into a rule — snapshots can name symbols that were since renamed or removed.
- **Dedup against existing memory**: before proposing, check the target `SKILL_MEMORY.md`/`GLOBAL_SKILL_MEMORY.md` for an equivalent rule; if present, propose an update/merge, not a duplicate.
- **Cluster across snapshots**: if multiple entries carry `feedback` snapshots about the same skill/topic, merge them into one coherent rule rather than N fragments.

Cross-skill overlap signal — the Step 1 diagnostic counts (non-zero) still flag prior attribution/merge errors worth reviewing.

> Note: the former code-statistics patterns (correction cluster / module hotspot / complexity concentration) were retired along with the scoring subsystem — schema:4 entries carry no `modules`/`score`/`correction` data. Only legacy schema:1-3 entries could still support them; do not expect them on new data.

### Step 3: Generate Proposals

For each pattern, produce a proposal containing:
1. Operation: Append, Merge, or Retire (Rule 3)
2. Target skill and file (Rule 2)
3. Full content with Anchors and Related fields
4. Evidence: timestamps of supporting traces + the memory snapshot slug(s) they came from
5. Risk note and confidence

Pre-write check: capacity headroom; for Retire, grep evidence that anchors are absent from current code.

When snapshot content and anchor evidence disagree on which skill owns a rule, present BOTH candidate skills in Step 4 for user choice.

### Step 4: User Approval

Present proposals one at a time:
- **Append** — full new entry
- **Merge** — original, merged version, and diff
- **Retire** — content + grep verification + `[RETIRED]` effect

Rejection records an `EVOLVE_REJECTION` entry with pattern name, reason, and future scope effect.

### Step 5: Write & Mark Processed

Atomic write (temp + rename). Replace analyzed entries with one audit line:

```
<!-- PROCESSED ts:{ISO8601} entries:{N} proposals:{M} -->
```

Delete `.trace_lock` in finally block.

### Step 6: Calibrate (Optional)

The score-weight calibration step was retired with the scoring subsystem (schema:4 has no dimensions to tune). If snapshot capture itself seems mis-scoped — e.g. too many low-value `project` snapshots, or `feedback` rules never landing — that is a hook/config issue (`memory_dir_pattern`, excluded types), not something to calibrate here; note it for the user instead.
