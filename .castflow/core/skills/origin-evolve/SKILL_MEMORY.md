# origin-evolve - Hard Rules

**This document's nature**: Mandatory constraints for the evolution analysis process.

---

### Rule 1: Evidence-Based Proposals Only

**Definition**: Every proposal must cite specific trace entries as evidence. No speculative improvements.

**Check list**:
- [ ] Does the proposal reference at least 2 concrete trace entries (by timestamp or sequence)?
- [ ] Is the pattern consistent across those entries (same root cause)?
- [ ] Would someone reading only the evidence agree with the conclusion?

---

### Rule 2: Correct Attribution

**Definition**: Proposed changes must be written to the correct file based on scope.

**Attribution decision tree**:

Step 1 - Determine target skill:
- modules contains only 1 module with a matching programmer-*-skill -> that skill
- modules contains 2+ modules with no common parent -> `.claude/rules/` as cross-cutting rule
- modules contains 2+ modules under same parent (e.g. Building+Queue under City) -> parent module's skill
- skills field is empty (knowledge gap) -> update the most related skill's SKILL.md description

Step 2 - Determine target file within skill:
- Correction pattern (AI repeatedly made same mistake) -> SKILL_MEMORY.md (add rule to prevent)
- Complexity concentration (high edit_count on specific file) -> EXAMPLES.md (add usage example)
- Module hotspot (module combo pattern) -> SKILL_MEMORY.md (add collaboration constraint)
- Knowledge gap (no skill matched) -> SKILL.md metadata (expand trigger keywords)

Other targets:
- Project-wide convention -> suggest user add to CLAUDE.md (do not write directly)
- Scoring model adjustment -> `traces/weights.json` (only via Step 6 calibration)

**Check list**:
- [ ] Did you follow the decision tree (not guess)?
- [ ] If targeting CLAUDE.md, is it phrased as a suggestion?
- [ ] If creating `.claude/rules/`, is the rule substantial enough?

---

### Rule 3: Knowledge Lifecycle Operations

**Definition**: Writing to Skill files supports three operations, not just append. Each requires user approval.

**Append** - Adding a new entry:
- Condition: New pattern, no similar entry exists in target file
- Format: Follow target file's existing numbering and heading style
- The new entry must include Anchors and Related fields (see Rule 8)

**Merge** - Combining with an existing entry:
- Condition: New pattern is closely related to an existing entry (same root cause or same code area)
- Action: Expand the existing entry's definition and check list, not create a duplicate
- Must show the user: original entry, proposed merged version, and the diff
- Numbering stays the same, content becomes more comprehensive

**Retire** - Marking an entry as inactive:
- Condition: Anchor verification shows the entry's code symbols no longer exist in the project, OR user explicitly requests retirement during review
- Action: Add `[RETIRED]` marker to the entry heading. Do NOT delete the entry
- Retired entries are skipped by AI when loading SKILL_MEMORY but preserved for history
- User can remove the marker to reactivate at any time

**Check list**:
- [ ] Is the operation type (Append/Merge/Retire) explicitly stated in the proposal?
- [ ] For Merge: is the diff shown to the user?
- [ ] For Retire: is anchor verification evidence provided?
- [ ] Does the user approve before any write?

---

### Rule 4: Proposal Threshold

**Definition**: Only propose when the benefit clearly outweighs the cost.

**Propose when**:
- Pattern appears in 3+ traces with consistent behavior
- The pattern has measurable impact signals (correction fields, high edit_count, cross-module repetition)
- The fix is concrete and actionable (not vague advice)

**Do not propose when**:
- Pattern appeared only once or twice (could be coincidence)
- Impact is negligible (minor style preference, not a real problem)
- The fix would be overly restrictive (high false positive risk)
- A similar proposal was previously rejected (check EVOLVE_REJECTION entries)

**Check list**:
- [ ] Does the pattern meet the 3+ occurrence threshold?
- [ ] Is the impact measurable and significant?
- [ ] Has a similar proposal been rejected before?

---

### Rule 5: Respect SKILL_ITERATION Standards

**Definition**: All generated content must comply with SKILL_ITERATION.md file size limits and format rules.

**Check list**:
- [ ] No emoji or special symbols?
- [ ] No dates, timestamps, or version markers?
- [ ] No code blocks in SKILL_MEMORY.md entries?
- [ ] File size stays within SKILL_ITERATION limits after the operation?

---

### Rule 6: Do Not Modify Hook-Generated Fields

**Definition**: When supplementing trace entries, only modify placeholder fields. Never modify Hook-generated fields.

**Protected fields**: timestamp, modules, files_modified, file_count, lines_changed, edit_count, score, correction (when auto-filled)

**Check list**:
- [ ] Is the modification limited to `type` and `skills` fields?
- [ ] Are Hook-generated values left untouched?

---

### Rule 7: Capacity Governance and Entry Format

**Definition**: Before writing to any Skill file, follow SKILL_ITERATION.md's capacity governance rules (Append/Merge/Retire operations and Anchors/Related entry format).

**Check list**:
- [ ] Was word count checked before proposing the write?
- [ ] Does the entry include Anchors and Related fields (per SKILL_ITERATION)?
- [ ] If over recommended range, is a Merge or Retire included in the proposal?
- [ ] For Retire: was Anchor grep verification performed?
- [ ] After all operations, does the file stay within SKILL_ITERATION warning threshold?

---

## Common Pitfalls

### Pitfall 1: Over-proposing

**Symptom**: Generating 10+ proposals from 20 traces, most with low confidence.

**Prevention**: Apply Rule 4 strictly. 2-3 high-confidence proposals are worth more than 10 speculative ones.

### Pitfall 2: Writing to Wrong File

**Symptom**: Adding a building-specific rule to GLOBAL_SKILL_MEMORY, or a cross-cutting rule to a single skill.

**Prevention**: Follow Rule 2 decision tree. When uncertain, prefer narrower scope.

### Pitfall 3: Proposing What Was Already Rejected

**Symptom**: Re-proposing a pattern the user previously rejected.

**Prevention**: Always check EVOLVE_REJECTION entries in trace.md. Respect user's reasoning.

### Pitfall 4: Vague Proposals

**Symptom**: Proposal says "improve error handling" without specifics.

**Prevention**: Every proposal needs concrete target file, concrete content, and concrete evidence.

### Pitfall 5: Ignoring edit_count Signal

**Symptom**: Only analyzing correction and modules, missing complexity concentration.

**Prevention**: Check for high edit_count + low file_count patterns. These indicate AI struggled with specific code.

### Pitfall 6: Append Without Capacity Check

**Symptom**: SKILL_MEMORY.md grows past 2000 words because every evolve cycle appends new entries without checking.

**Prevention**: Always run Rule 7 capacity check before proposing any Append. If over recommended range, propose a Merge or Retire first.

### Pitfall 7: Merging Without User Diff Review

**Symptom**: Silently combining two entries, losing nuance from the original.

**Prevention**: Merge must always show the user the before/after diff. The user decides if the merge preserves the intent of both entries.

---
