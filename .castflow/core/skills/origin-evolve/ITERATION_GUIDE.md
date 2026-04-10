# Origin Evolve - Iteration Guide

---

## Skill Positioning

Core responsibilities of this skill (aligned with SKILL.md):
1. Read and analyze execution traces from `.claude/traces/trace.md`
2. Identify actionable patterns with sufficient evidence
3. Generate proposals with correct attribution and concrete content
4. Apply approved changes to the right files in the right format

Target users: Project developers who want their AI knowledge base to improve over time.

---

## Iteration Rules

### Rule 1: Update Analysis Dimensions

**Trigger**: New types of trace data become available (e.g., new fields added to trace format)
**Priority**: Medium
**File**: SKILL.md (Step 2 pattern types)
**Check list**:
- [ ] Are all trace fields being used in analysis?
- [ ] Are there new pattern categories to add?

---

### Rule 2: Update Proposal Examples

**Trigger**: A new type of proposal is successfully applied and proves valuable
**Priority**: Medium
**File**: EXAMPLES.md
**Check list**:
- [ ] Does the new proposal type have a representative example?
- [ ] Does the example show the full cycle (trace data -> analysis -> proposal -> application)?

---

### Rule 3: Update Threshold Calibration

**Trigger**: Users consistently approve or reject proposals at certain confidence levels
**Priority**: High
**File**: SKILL_MEMORY.md (Rule 4 thresholds)
**Check list**:
- [ ] Are the occurrence thresholds still appropriate?
- [ ] Should the confidence bar be raised or lowered based on user feedback?

---

## File Responsibilities

| File | When to modify | Forbidden content |
|------|---------------|------------------|
| SKILL.md | Analysis flow changes, new pattern types | Code examples, rule definitions |
| EXAMPLES.md | New proposal types, format changes | Rule definitions, dates |
| SKILL_MEMORY.md | New constraints discovered, threshold adjustments | Dates, version info, code blocks |
| ITERATION_GUIDE.md | Skill scope changes | Dates, historical logs |

---

## Quality Metrics

**Metric 1**: Proposal acceptance rate
  Target: Above 70%
  Measurement: Count approved vs rejected proposals over time

**Metric 2**: Proposal impact
  Target: Approved proposals lead to measurable improvement (fewer retries in subsequent traces)
  Measurement: Compare retry rate before and after proposal application

**Metric 3**: False positive rate
  Target: Below 10% of proposals are rejected as "too aggressive" or "wrong scope"
  Measurement: Track rejection reasons

---
