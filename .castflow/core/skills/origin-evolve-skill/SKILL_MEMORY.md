# origin-evolve-skill - Hard Rules

Mandatory constraints. Violation = invalid execution.

---

### Rule 1: Evidence-Based Proposals

Every proposal cites 2+ trace entries (by timestamp) sharing one root cause. Single occurrences and speculative improvements are forbidden.

Self-check: would the proposal still hold if you removed the cited evidence? If yes, the evidence is incidental and the proposal is unfounded — drop it.

`validated:false` traces are P0 evidence regardless of correction signal. When 3+ such traces share one module with `correction:_`, compare `request` vs `intent` to identify systematic AI misunderstanding.

---

### Rule 2: Attribution Decision Tree

**Target skill** (in priority order):
1. One module with mapped `programmer-*-skill` -> that skill
2. Two or more modules under one common parent that owns a skill -> parent's skill
3. Two or more modules with no common parent -> `.claude/rules/`
4. `skills` field empty in cited traces -> SKILL.md description of the closest skill

**Anchor evidence as secondary signal**: when the proposed rule's significant anchors (excluding generic symbols such as `OnDestroy`, `Subscribe`, `AddTimer`, `LoadAsset`) are owned by an existing skill different from the module-list result, surface BOTH candidates in Step 4 for user choice. Do not auto-override.

**Target file within the skill**:
| Pattern | File |
|---------|------|
| Behavioral constraint | SKILL_MEMORY.md |
| Code pattern reference | EXAMPLES.md |
| Trigger keyword expansion | SKILL.md description |
| Project-wide convention | suggest CLAUDE.md (do not write directly) |

---

### Rule 3: Append / Merge / Retire

| Operation | Trigger | Required evidence |
|-----------|---------|-------------------|
| Append | No existing rule with anchor Jaccard >= 0.5 against the proposal | Full new entry with Anchors (prefer extended format `kind:path-hint:symbol`) and Related |
| Merge | Existing rule with anchor Jaccard >= 0.5 | Diff showing anchor union and content delta |
| Retire | Anchor symbols absent from current code (use path-hint if available to narrow grep scope) | `grep` output proving 0 matches |

Thresholds (Jaccard, capacity word count) read from `traces/governance.json` with defaults: Jaccard 0.5, file capacity 2000 words. If file is over capacity, propose Retire of an obsolete entry before Append.

Retired entries: prepend `[RETIRED]` to the heading. Never delete content; AI consumers skip retired entries by convention.

---

### Rule 4: User Approval Required for Every Write

No proposal may be written without explicit user approval. This includes Append, Merge, Retire, and weight calibration.

Hook-generated trace fields (`timestamp`, `modules`, `files_modified`, `file_count`, `lines_changed`, `edit_count`, `score`, `correction`) are read-only; never modify them when supplementing trace entries (`type`, `skills`, `mode`, `request`, `intent` only).

CLAUDE.md changes are always proposed as suggestions to the user; never write directly.

---

### Rule 5: Format & Capacity Compliance

All generated content follows `.castflow/core/skills/SKILL_ITERATION.md` format rules: no emoji, no dates, no code blocks in SKILL_MEMORY entries.

Before writing: verify file is within capacity. New SKILL_MEMORY entries must include `Anchors:` (prefer extended format `[kind:path-hint:symbol]` for precision) and `Related:` (cross-references). For Retire, use path-hint to narrow grep scope when available; anchors must be `grep`-verified absent.

---

## Pitfalls

**P1: Wrong file target** — Building-specific rule landing in GLOBAL_SKILL_MEMORY, or cross-cutting rule in one skill. Apply Rule 2; prefer narrower scope when uncertain. Cross-skill overlap signals from Step 1 are direct evidence of past P1 errors.

**P2: Re-proposing rejected patterns** — Always scan `EVOLVE_REJECTION` entries first. A rejected proposal carries scope guidance that future proposals must respect.

**P3: Vague proposals** — "Improve error handling" is not a proposal. Required: concrete file + concrete content + named evidence (timestamps).
