# origin-evolve - Hard Rules

**This document's nature**: Mandatory constraints for the evolution analysis process.

---

### Rule 1: Evidence-Based Proposals Only

Every proposal must cite 2+ concrete trace entries (by timestamp) with consistent pattern (same root cause). No speculative improvements. Check: evidence independently supports conclusion?

---

### Rule 2: Correct Attribution

**Target skill**:
- 1 module with matching programmer-*-skill -> that skill
- 2+ modules, no common parent -> `.claude/rules/` (cross-cutting rule)
- 2+ modules under same parent -> parent module's skill
- skills field empty -> most related skill's SKILL.md description

**Target file**:
- Correction pattern -> SKILL_MEMORY.md
- Complexity concentration (high edit_count) -> EXAMPLES.md
- Module hotspot -> SKILL_MEMORY.md
- Knowledge gap -> SKILL.md metadata (expand trigger keywords)
- Project-wide convention -> suggest adding to CLAUDE.md (never write directly)
- Scoring model -> `traces/weights.json` (only via Step 6)

Check: Followed decision tree? CLAUDE.md phrased as suggestion?

---

### Rule 3: Knowledge Lifecycle Operations

| Operation | Condition | Action |
|-----------|-----------|--------|
| Append | No similar entry exists | Add with Anchors + Related |
| Merge | Overlaps existing entry (same root cause/code area) | Expand existing; show diff |
| Retire | Anchors no longer exist (grep-verified) or user requests | Add [RETIRED] to heading; do NOT delete |

All operations require user approval. Merge must show diff. Retire must show grep evidence.

---

### Rule 4: Proposal Threshold

Propose only when: 3+ trace occurrences, measurable impact (correction/high edit_count/cross-module), concrete fix, not previously rejected (check EVOLVE_REJECTION entries). Do not propose for single occurrences or negligible impact.

---

### Rule 5: File Standards and Capacity

All generated content must comply with SKILL_ITERATION.md size limits and format rules: no emoji, no dates/timestamps, no code blocks in SKILL_MEMORY entries. Before writing: check word count, ensure Anchors + Related fields, propose Merge or Retire if over range, grep-verify anchors before Retire.

---

### Rule 6: Do Not Modify Hook-Generated Fields

Only modify `type` and `skills` when supplementing trace entries. Never touch: timestamp, modules, files_modified, file_count, lines_changed, edit_count, score, correction (when auto-filled).

---

### Rule 7: Trace Entry Lifecycle

States: `pending` (eligible), `processed` (audit line), `expired` (validation window elapsed), `invalid` (pipeline abandoned).

Step 0 transitions: `pending` with stale validated -> `expired`; `pending-pipeline` past expiry -> `invalid`. Old-format entries (no validated field): treat as `validated:_`, eligible if they carry correction signals.

---

### Rule 8: P0 Semantic Drift

`validated:false` is always P0 regardless of correction. Sub-sort: auto:major > auto:minor > _. When 3+ P0 entries share a module with `correction:_`, compare request vs intent to identify systematic misunderstanding; propose intent-clarification rule.

---

### Rule 9: .trace_lock Management

Write at Step 0 start; delete in finally block after Step 5. Stale lock = overwrite (not blocker). Lock signals trace-flush to skip compaction; appends always safe. Single-session assumption.

---

## Common Pitfalls

**Pitfall 1: Over-proposing** -- 10+ proposals from 20 traces = low confidence. Target 2-3 high-confidence proposals.

**Pitfall 2: Wrong file target** -- Building-specific rule in GLOBAL_SKILL_MEMORY, or cross-cutting in one skill. Follow Rule 2 decision tree; prefer narrower scope when uncertain.

**Pitfall 3: Re-proposing rejected patterns** -- Always check EVOLVE_REJECTION entries first.

**Pitfall 4: Vague proposals** -- "improve error handling" is not a proposal. Requires: concrete target, content, and evidence.

**Pitfall 5: Ignoring edit_count** -- High edit_count + low file_count = AI struggled with that file. Check complexity concentration.

**Pitfall 6: Append without capacity check** -- Run Rule 5 capacity check before every Append.

**Pitfall 7: Compaction deleting pending-pipeline** -- All compression must skip `validated:pending-pipeline` entries awaiting Step 5 results.
