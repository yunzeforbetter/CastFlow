---
name: origin-evolve-skill
description: origin evolve trace.md execution trace hook pattern proposal knowledge update validated protocol skill files compact trace NOT code_pipeline NOT bootstrap
---

# Origin Evolve

Mission: turn `.claude/traces/trace.md` into approved updates of `.claude/skills/`.

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

## Trace Fields (schema:2)

Hook-generated (read-only): `timestamp`, `modules`, `score`, `score_breakdown`, `correction`, `pipeline_run_id`.

AI-supplemented (via IDP `.pending_idp.json`): `mode`, `type`, `skills`, `error_cause`, `fix_approach`, `user_feedback`, `lesson`.

Lifecycle: `status` (pending/processed/expired/invalid), `validated` (`_`/true/false/pending-pipeline/invalid).

The experience fields (`error_cause`, `fix_approach`, `user_feedback`, `lesson`) carry the core learning value. Entries where they are `_` are low-signal skeletons; prioritize entries where they are populated.

## Execution Flow

```
Step 1 Read & Triage -> Step 2 Identify Patterns -> Step 3 Generate Proposals -> Step 4 User Approval -> Step 5 Write & Mark Processed -> Step 6 Calibrate (optional)
```

### Step 1: Read & Triage

Acquire `.trace_lock` (overwrite if stale). Apply lifecycle transitions: `pending` with stale validated -> `expired`; `pending-pipeline` past expiry -> `invalid`.

**Schema version gate**: the current trace schema is `2`. Entries without a schema tag are treated as schema 1 (legacy, backward compatible — the removed `files_modified`/`file_count`/`lines_changed`/`edit_count`/`request`/`intent` fields simply read as absent). Accept `schema:1` and `schema:2`. If any entry has `schema:N` where N > 2, abort and report "Unsupported trace schema version N. Update origin-evolve."

Read trace.md, keep `pending` only, then exclude entries with `validated:pending-pipeline` from proposal candidates until they are finalized to `true` / `false` or expire to `invalid`. If fewer than 5 analyzable pending entries remain and no correction signals exist, suggest waiting.

Compute three diagnostic counts across `.claude/skills/*/SKILL_MEMORY.md` and include in the analysis summary:
- within-skill rule pairs with anchor Jaccard >= 0.5
- cross-skill identical anchor sets
- cross-skill rule pairs with anchor Jaccard >= 0.5

Non-zero counts indicate prior attribution or merge errors and should inform Step 2 proposal generation.

Sort priority:
- Exclude `validated:pending-pipeline` from the priority queue; they are runtime-in-flight, not proposal evidence.
- P0: `validated:false` (sub-sort: auto:major > auto:minor > `_`)
- P1: `validated:true` + correction:auto:major
- P2: `validated:true` + correction:auto:minor
- P3: `validated:_` with any correction signal
- P4: `validated:_`, no correction (by score desc)

### Step 2: Identify Patterns

Focus on high-leverage signals; require 3+ supporting traces:
- **Correction cluster** — same module, multiple `correction` entries -> module lacks rule guidance
- **Module hotspot** — same module pair co-occurring -> undocumented cross-module dependency
- **Complexity concentration** — same module with high `E` in `score_breakdown` (edit intensity) recurring across traces -> missing usage examples
- **Cross-skill overlap signal** — Step 1 diagnostic counts non-zero -> attribution review candidate

Speculative patterns (use only with overwhelming evidence): knowledge gap (`skills:[]`), semantic drift (`validated:false` + `correction:_`), IDP gap (`mode:_` dominant).

### Step 3: Generate Proposals

For each pattern, produce a proposal containing:
1. Operation: Append, Merge, or Retire (Rule 3)
2. Target skill and file (Rule 2)
3. Full content with Anchors and Related fields
4. Evidence: timestamps + modules of supporting traces
5. Risk note and confidence

Pre-write check: capacity headroom; for Retire, grep evidence that anchors are absent from current code.

When module-list and anchor evidence disagree on attribution, present BOTH candidate skills in Step 4 for user choice.

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

When 20+ entries processed in this run, compare F/D/K/S/E dimension means between proposal-yielding traces and non-yielding traces. Adjust the dimension with the largest gap by 5-10% (weights 0.2-3.0, thresholds 1.0-3.0). At most one dimension per run.
