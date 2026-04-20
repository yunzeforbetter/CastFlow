---
name: origin-evolve
description: Analyze execution traces to extract patterns, propose improvements to Skills/Memory, and drive self-evolution of the AI knowledge base
---

# Origin Evolve - Self-Evolution Engine

**Core mission**: Read execution traces, identify recurring patterns, propose improvements (with evidence), and write approved changes to the correct knowledge files.

**Responsibilities**:
1. Read `.claude/traces/trace.md` and rank entries by priority
2. Detect six pattern types across structured trace fields
3. Generate proposals with evidence, attribution, and risk assessment
4. Write approved changes to the correct Skill files
5. Optionally calibrate scoring weights (`traces/weights.json`)

**Data flow**: Hook scripts create trace entries -> AI supplements type/skills/mode/request/intent -> trace-flush injects validated signal -> this Skill consumes all fields for analysis.

---

## Quick Navigation

| Need to know | See |
|-------------|------|
| Proposal formats and analysis examples | EXAMPLES.md |
| Hard rules and common pitfalls | SKILL_MEMORY.md |
| Iteration and maintenance | ITERATION_GUIDE.md |

---

## Trace Entry Fields

**Hook-generated (read-only)**: timestamp, correction, modules, files_modified, file_count, lines_changed, edit_count, score

**AI-supplemented**: type, skills, mode, request, intent

**trace-flush injected**: validated (_/true/false/pending-pipeline/invalid)

**correction**: _ (none) | auto:minor (1-2 fixes) | auto:major (3+ fixes) | minor/major (AI manual)

**validated**: _ (no signal) | true (accepted) | false (rejected=P0) | pending-pipeline (awaiting Step 5) | invalid (abandoned)

---

## Execution Flow

```
Trigger -> Step 0 Lifecycle -> Step 1 Read & Sort -> Step 2 Pattern Detection -> Step 3 Generate Proposals -> Step 4 User Approval -> Step 5 Mark Processed -> Step 6 Calibrate (optional) -> Release lock
```

**Trigger**: User inputs `origin evolve` or similar intent.

### Step 0: Lifecycle Pre-processing

1. Write `.trace_lock` (overwrite if stale). Read `traces/limits.json` for expiry thresholds.
2. State transitions: `pending-pipeline` past expiry -> `invalid`; `pending` with `_`/`false` validated past expiry -> `expired`.
3. Log transition counts in analysis summary (no separate file).

### Step 1: Read and Sort

Read trace.md, skip `processed`/`expired`/`invalid`. If < 5 pending entries, suggest waiting.

Priority order:
- P0: `validated:false` (sub-sort: auto:major > auto:minor > _)
- P1: `validated:true` + `correction:auto:major`
- P2: `validated:true` + `correction:auto:minor`
- P3: `validated:_` + any correction signal
- P4: `validated:_` + `correction:_` (by score desc)
- Old-format entries (no validated): treat as `validated:_`

### Step 2: Pattern Detection

Six pattern types from sorted traces:

| Pattern | Signal | Indicates |
|---------|--------|-----------|
| Correction | correction non-_ clusters by module | Module lacks rule guidance |
| Module hotspot | modules field co-occurrence | Undocumented cross-module dependency |
| Knowledge gap | skills field empty | Skill metadata needs expansion |
| Complexity concentration | high edit_count, low file_count | Missing usage rules/examples for file |
| Semantic drift | 3+ validated:false + correction:_ same module | Systematic AI misunderstanding |
| IDP gap | mode:_ dominant in module | Information identification rules missing |

### Step 3: Generate Proposals (with governance)

For each pattern:

**3a. Attribution**: Follow SKILL_MEMORY Rule 2 decision tree for target skill and file.

**3b. Operation type**: Check if semantically similar entry exists -> Merge (yes) or Append (no).

**3c. Capacity check**: Count target file words. If over threshold -> attach Retire suggestion. Retire candidates: grep-verify anchors; missing anchors = eligible.

**3d. Assemble**: operation type, phenomenon, evidence (timestamps+modules), change content (diff for Merge), target file, benefit, risk, confidence. Only propose when confidence high and benefit outweighs risk.

### Step 4: User Approval

Present proposals individually with operation-specific detail:
- **Append**: Full new entry with Anchors and Related
- **Merge**: Original, merged version, and diff
- **Retire**: Content, grep verification, [RETIRED] effect

Rejections recorded as EVOLVE_REJECTION in trace.md with pattern, reason, and future effect.

### Step 5: Mark Processed

Replace analyzed entries with: `<!-- PROCESSED ts:{ISO8601} entries:{N} proposals:{M} -->`

Write atomically (temp file + rename). Delete `.trace_lock` in finally block.

### Step 6: Calibrate Scoring (optional)

When 20+ entries processed: compare dimensions between proposal-yielding and non-yielding traces. Adjust weights +/-5-10% (max 10% per adjustment, range 0.2-3.0, threshold 1.0-3.0). Ensure `.trace_lock` deleted in finally block.
