# origin-evolve-skill-memory - Evolution Hard Rules

**This document's nature**: Mandatory constraints for the evolution analysis process.

---

### Rule 1: Evidence-Based Proposals Only

**Definition**: Every proposal must cite specific trace entries as evidence. No speculative improvements.

**Check list**:
- [ ] Does the proposal reference at least 2 concrete trace entries?
- [ ] Is the pattern consistent across those entries (same root cause)?
- [ ] Would someone reading only the evidence agree with the conclusion?

---

### Rule 2: Correct Attribution

**Definition**: Proposed changes must be written to the correct file based on scope.

**Attribution rules**:
- Single-skill pattern -> that skill's SKILL_MEMORY.md
- Cross-skill pattern with no single owner -> `.claude/rules/` as standalone .md
- Code pattern/usage example -> that skill's EXAMPLES.md
- Skill discovery improvement -> that skill's SKILL.md metadata
- Project-wide convention -> suggest user add to CLAUDE.md (do not write directly)

**Check list**:
- [ ] Is the target file correct per attribution rules?
- [ ] If targeting CLAUDE.md, is it phrased as a suggestion to the user?
- [ ] If creating a new file in `.claude/rules/`, is the rule substantial enough to warrant its own file?

---

### Rule 3: Append-Only Writing

**Definition**: When writing to existing files, only append new content. Never modify or delete existing entries.

**Check list**:
- [ ] Is the change an append operation (not a modification)?
- [ ] Does the appended content follow the target file's existing format?
- [ ] Is the rule/entry numbered sequentially after existing entries?

---

### Rule 4: Proposal Threshold

**Definition**: Only propose when the benefit clearly outweighs the cost. Not every observation deserves a proposal.

**Propose when**:
- Pattern appears in 3+ traces with consistent behavior
- The pattern caused measurable impact (retries, user corrections, NO-GO)
- The fix is concrete and actionable (not vague advice)

**Do not propose when**:
- Pattern appeared only once or twice (could be coincidence)
- Impact is negligible (minor style preference, not a real problem)
- The fix would be overly restrictive (high false positive risk)
- A similar proposal was previously rejected by the user

**Check list**:
- [ ] Does the pattern meet the 3+ occurrence threshold?
- [ ] Is the impact measurable and significant?
- [ ] Has a similar proposal been rejected before (check EVOLVE_REJECTION entries)?

---

### Rule 5: Respect SKILL_RULE Standards

**Definition**: All generated content must comply with SKILL_RULE.md. This applies to any content appended to Skill files.

**Check list**:
- [ ] No emoji or special symbols in generated content?
- [ ] No dates, timestamps, or version markers?
- [ ] No code blocks in SKILL_MEMORY.md entries?
- [ ] File size stays within SKILL_RULE limits after append?

---

## Common Pitfalls

### Pitfall 1: Over-proposing

**Symptom**: Generating 10+ proposals from 20 traces, most with low confidence.

**Prevention**: Apply Rule 4 strictly. Quality over quantity. 2-3 high-confidence proposals are worth more than 10 speculative ones.

### Pitfall 2: Writing to Wrong File

**Symptom**: Adding a building-specific rule to GLOBAL_SKILL_MEMORY, or adding a cross-cutting rule to a single skill's memory.

**Prevention**: Apply Rule 2 attribution rules. When uncertain, prefer the narrower scope (skill-specific over global).

### Pitfall 3: Proposing What Was Already Rejected

**Symptom**: Re-proposing a pattern the user previously rejected.

**Prevention**: Always check EVOLVE_REJECTION entries in trace.md before finalizing proposals. Respect user's reasoning.

### Pitfall 4: Vague Proposals

**Symptom**: Proposal says "improve error handling" without specifying what, where, or how.

**Prevention**: Every proposal must have a concrete target file, concrete content to write, and concrete evidence. If it cannot be made concrete, it is not ready to propose.

---
