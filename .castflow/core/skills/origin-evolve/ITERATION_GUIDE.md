# Origin Evolve - Iteration Guide

---

## Skill Positioning

Core responsibilities of this skill (aligned with SKILL.md):
1. Read and analyze execution traces from `.claude/traces/trace.md`
2. Identify actionable patterns using structured trace fields (correction, modules, edit_count, score, skills)
3. Generate proposals with correct attribution and concrete content
4. Apply approved changes to the right files in the right format
5. Optionally calibrate scoring model weights via `traces/weights.json`

Target users: Project developers who want their AI knowledge base to improve over time.

---

## Iteration Rules

### Rule 1: Update Analysis Dimensions

**Trigger**: New fields added to trace format or new pattern categories discovered
**Priority**: Medium
**File**: SKILL.md (Step 2 pattern types, Trace field table)
**Check list**:
- [ ] Are all trace fields being used in analysis?
- [ ] Are there new pattern categories to add?
- [ ] Is the Trace field table up to date?

---

### Rule 2: Update Proposal Examples

**Trigger**: A new type of proposal is successfully applied and proves valuable
**Priority**: Medium
**File**: EXAMPLES.md
**Check list**:
- [ ] Does the new proposal type have a representative example?
- [ ] Does the example show the full cycle (trace data -> analysis -> proposal -> application)?
- [ ] Does the trace data in examples use the current field format?

---

### Rule 3: Update Threshold Calibration

**Trigger**: Users consistently approve or reject proposals at certain confidence levels
**Priority**: High
**File**: SKILL_MEMORY.md (Rule 4 thresholds)
**Check list**:
- [ ] Are the occurrence thresholds still appropriate?
- [ ] Should the confidence bar be raised or lowered based on user feedback?

---

### Rule 4: Update Scoring Model Guidance

**Trigger**: weights.json calibration reveals systematic bias in trace admission
**Priority**: Medium
**File**: SKILL.md (Step 6 calibration guidance)
**Check list**:
- [ ] Are the weight adjustment bounds still reasonable?
- [ ] Should new dimensions be added to the scoring model?
- [ ] Is the calibration trigger threshold (20+ processed entries) still appropriate?

---

## File Responsibilities

| File | When to modify | Forbidden content |
|------|---------------|------------------|
| SKILL.md | Analysis flow changes, new pattern types, trace field updates | Code examples, rule definitions |
| EXAMPLES.md | New proposal types, format changes | Rule definitions, dates |
| SKILL_MEMORY.md | New constraints discovered, threshold adjustments | Dates, version info, code blocks |
| ITERATION_GUIDE.md | Skill scope changes | Dates, historical logs |

---

## Quality Metrics

**Metric 1**: Proposal acceptance rate
  Target: Above 70%
  Measurement: Count approved vs rejected proposals over time

**Metric 2**: Correction reduction
  Target: Approved proposals lead to fewer correction signals in subsequent traces
  Measurement: Compare correction frequency before and after proposal application

**Metric 3**: False positive rate
  Target: Below 10% of proposals are rejected as "too aggressive" or "wrong scope"
  Measurement: Track EVOLVE_REJECTION entries and their reasons

---
