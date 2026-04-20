# Origin Evolve - Iteration Guide

This skill evolves only when the trace data model or the proposal taxonomy changes.

## Iteration Rules

### Rule 1: New Trace Field

**Trigger**: hook scripts emit a new field, or AI-supplemented field semantics change.
**Files**: SKILL.md (Trace Fields section, sort priority, pattern detectors).
**Check**: Step 1 sort and Step 2 patterns reference the new field where applicable.

### Rule 2: New Proposal Operation

**Trigger**: an operation that does not fit Append / Merge / Retire.
**Files**: SKILL_MEMORY.md Rule 3 (operation table), EXAMPLES.md (one demonstration).
**Check**: Operation, trigger condition, and required evidence are all defined; one example shows full cycle.

### Rule 3: Threshold or Bound Change

**Trigger**: defaults in `traces/governance.json` change, or weight bounds in `weights.json` prove wrong in practice.
**Files**: SKILL_MEMORY.md Rule 3 (Jaccard, capacity), SKILL.md Step 6 (calibration bounds).
**Check**: Same numbers cited in all locations.

## File Boundaries

Global standard: `.castflow/core/SKILL_ITERATION.md`.

Origin-evolve specific:
- SKILL.md does not embed raw trace markdown
- EXAMPLES.md does not restate Rule definitions
- SKILL_MEMORY.md does not embed full code blocks
