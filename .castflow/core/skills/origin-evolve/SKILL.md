---
name: origin-evolve
description: Read execution traces, identify patterns, propose knowledge changes, write after approval
---

# Origin Evolve

Mission: turn `.claude/traces/trace.md` into approved updates of `.claude/skills/`.

Trigger: user input `origin evolve` (or equivalent intent).

## Quick Navigation

| Need | See |
|------|-----|
| How proposals look end-to-end | EXAMPLES.md |
| Hard constraints on every change | SKILL_MEMORY.md |
| When to update this skill | ITERATION_GUIDE.md |

## Trace Fields

Hook-generated (read-only): `timestamp`, `modules`, `files_modified`, `file_count`, `lines_changed`, `edit_count`, `score`, `correction`.

AI-supplemented: `type`, `skills`, `mode`, `request`, `intent`.

Lifecycle: `status` (pending/processed/expired/invalid), `validated` (`_`/true/false/pending-pipeline/invalid).

## Execution Flow

```
Step 1 Read & Triage -> Step 2 Identify Patterns -> Step 3 Generate Proposals -> Step 4 User Approval -> Step 5 Write & Mark Processed -> Step 6 Calibrate (optional)
```

### Step 1: Read & Triage

Acquire `.trace_lock` (overwrite if stale). Apply lifecycle transitions: `pending` with stale validated -> `expired`; `pending-pipeline` past expiry -> `invalid`.

Read trace.md, keep `pending` only. If fewer than 5 pending entries and no correction signals, suggest waiting.

Compute three diagnostic counts across `.claude/skills/*/SKILL_MEMORY.md` and include in the analysis summary:
- within-skill rule pairs with anchor Jaccard >= 0.5
- cross-skill identical anchor sets
- cross-skill rule pairs with anchor Jaccard >= 0.5

Non-zero counts indicate prior attribution or merge errors and should inform Step 2 proposal generation.

Sort priority:
- P0: `validated:false` (sub-sort: auto:major > auto:minor > `_`)
- P1: `validated:true` + correction:auto:major
- P2: `validated:true` + correction:auto:minor
- P3: `validated:_` with any correction signal
- P4: `validated:_`, no correction (by score desc)

### Step 2: Identify Patterns

Focus on high-leverage signals; require 3+ supporting traces:
- **Correction cluster** — same module, multiple `correction` entries -> module lacks rule guidance
- **Module hotspot** — same module pair co-occurring -> undocumented cross-module dependency
- **Complexity concentration** — single file with `edit_count` >= 10 across multiple traces -> missing usage examples
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
