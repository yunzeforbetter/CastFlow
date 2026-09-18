# origin-evolve-skill - Hard Rules

Mandatory constraints. Violation = invalid execution.

---

### Rule 1: Evidence-Based Proposals

A MEMORY subblock is eligible only when `(type is feedback AND quality is ok)` or `homologous_count >= 2`. One ok feedback snapshot can justify a proposal. `project` / `reference` / thin feedback need a homology component of size >= 2.

`validated` never grants eligibility. `validated:false` only ranks already-eligible items (P0) and counts the TRACE toward notify.

Self-check: would the proposal still hold if you removed the cited evidence? If yes, the evidence is incidental and the proposal is unfounded — drop it.

---

### Rule 2: Attribution Decision Tree

**Target** (in priority order):
1. Whitelisted `skill:` on the MEMORY subblock (runtime skill dir with SKILL.md, not origin-evolve-skill / skill-creator / goal-loop-creator) -> that skill
2. Else anchors hit exactly one project skill's existing Anchors -> that skill
3. Steps 1 and 2 both hit and disagree -> user pick (still a single skill write)
4. Anchors hit two or more different project skills -> `.castflow-runtime/rules/cross-cutting.md`
5. None of the above -> do not write a rule file; leave waiting

Never write `.claude/rules/` business rules. Never write GLOBAL_SKILL_MEMORY.md, CLAUDE.md, AGENTS.md, hook scripts, or origin-evolve itself.

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

Thresholds: Jaccard 0.5 (via `manager.py homology`, not this skill), file capacity 2000 words. If file is over capacity, propose Retire of an obsolete entry before Append.

Retired entries: prepend `[RETIRED]` to the heading. Never delete content; AI consumers skip retired entries by convention.

---

### Rule 4: User Approval Required for Every Write

No proposal may be written without explicit user approval. This includes Append, Merge, and Retire.

Trace entries (schema:4) are entirely hook-generated and read-only: `timestamp`, `type`, `validated`, `quality`, `gate_hint`, `memory_snapshots`, plus MEMORY `skill` / `anchors` / `quality`. There are no AI-supplemented fields. Distill rules from snapshot content; never fabricate or modify trace fields. Legacy fields (`pipeline_run_id`, `score`, `modules`, `correction`) may still appear; ignore them.

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
