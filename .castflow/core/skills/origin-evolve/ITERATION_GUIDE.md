# Origin Evolve - Iteration Guide

---

## Skill Positioning

Core responsibilities (aligned with SKILL.md):
1. Read and analyze execution traces from `.claude/traces/trace.md`
2. Identify actionable patterns using structured trace fields
3. Generate proposals with correct attribution and concrete content
4. Apply approved changes to the right files in the right format
5. Optionally calibrate scoring model weights

Target users: Project developers who want their AI knowledge base to improve over time.

---

## Iteration Rules

### Rule 1: Update Analysis Dimensions

**Trigger**: New fields added to trace format or new pattern categories discovered
**Priority**: Medium
**File**: SKILL.md (Step 2 pattern types, Trace field table)
**Check**: All trace fields used in analysis? New pattern categories needed? Field table current?

---

### Rule 2: Update Proposal Examples

**Trigger**: A new type of proposal is successfully applied and proves valuable
**Priority**: Medium
**File**: EXAMPLES.md
**Check**: New proposal type has representative example? Example shows full cycle (trace -> analysis -> proposal)?

---

### Rule 3: Update Threshold Calibration

**Trigger**: Users consistently approve or reject proposals at certain confidence levels
**Priority**: High
**File**: SKILL_MEMORY.md (Rule 4 thresholds)
**Check**: Occurrence thresholds appropriate? Confidence bar needs adjustment?

---

### Rule 4: Update Scoring Model Guidance

**Trigger**: weights.json calibration reveals systematic bias in trace admission
**Priority**: Medium
**File**: SKILL.md (Step 6 calibration guidance)
**Check**: Weight bounds reasonable? New dimensions needed? Calibration trigger threshold appropriate?

---

## File Responsibilities

| File | When to modify | Forbidden content |
|------|---------------|------------------|
| SKILL.md | Analysis flow changes, new pattern types | Code examples, rule definitions |
| EXAMPLES.md | New proposal types, format changes | Rule definitions, dates |
| SKILL_MEMORY.md | New constraints, threshold adjustments | Dates, version info, code blocks |
| ITERATION_GUIDE.md | Skill scope changes | Dates, historical logs |

---

## Quality Metrics

**Proposal acceptance rate**: Target above 70%. Count approved vs rejected over time.

**Correction reduction**: Approved proposals should reduce correction frequency in subsequent traces.

**False positive rate**: Target below 10% of proposals rejected as "too aggressive" or "wrong scope". Track via EVOLVE_REJECTION entries.
