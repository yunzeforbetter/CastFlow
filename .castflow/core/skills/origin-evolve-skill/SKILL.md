---
name: origin-evolve-skill
description: >
  Distill trace.md memory snapshots into skill rules. Use when the user
  says origin evolve, 沉淀规则, or evolve-reminder fired.
  NOT generating new module skills (skill-creator).
---

# Origin Evolve

Turn pending memory snapshots in `.castflow-runtime/traces/trace.md` into approved skill updates under `.castflow-runtime/skills/`. Never write adapter mirrors. After writes: `python .castflow/manager.py sync`.

Trigger: `origin evolve` (or the same intent). Never run unprompted.

## Yield

- Install / scan / UI -> **bootstrap-skill**
- Create a new module skill -> **bootstrap-skill** (pasted `/goal` loop-engine prompt)
- Requirement to a runnable long task -> **goal-loop-creator**
- Feature work in a module -> that **programmer-*-skill**

## Nav

| Need | See |
|------|-----|
| Proposal examples | EXAMPLES.md |
| Evidence / attribution / ops | SKILL_MEMORY.md |
| When to edit this skill | ITERATION_GUIDE.md |

## Trace (schema:4)

Hook-generated ledger. Fields: `timestamp`, `type`, `validated`, `quality`, `gate_hint`, `memory_snapshots`, plus MEMORY subblocks with `skill`, `anchors`, `quality`. Read-only. Ignore legacy `score` / `modules` / `pipeline_run_id` / `pending-pipeline`.

## Eligible (MEMORY grain)

`validated` does **not** grant eligibility. It only sorts already-eligible items and counts the TRACE toward notify.

```
eligible(m) =
  (m.type == feedback AND m.quality == ok)
  OR homologous_count(m) >= 2
```

`homologous_count(m)` is the size of m's connected component from `python .castflow/manager.py homology` (includes self). Singleton size is 1.

Do not invent Jaccard in this skill. Do not spawn one Python process per pair.

## Flow

```
Step 0 Flush if needed -> lock -> Step 1 Triage -> Step 2 Distill -> Step 3 Propose -> Step 4 Approve -> Step 5 Write
```

**Step 0.** If `.castflow-runtime/traces/.trace_memory_snapshots` exists, run `python .castflow/manager.py flush` **before** taking `.trace_lock`. Then create `.trace_lock`. If the snapshot store still exists, abort (do not call flush while holding the lock).

**Step 1.** Keep `pending` only. Do not expire on `validated:_`. Leftover `pending-pipeline` -> invalid. Abort if any `schema:N` with N > 4.

Cluster MEMORY subblocks with one `manager.py homology` call. Priority among **eligible** only: P0 TRACE `validated:false`; P1 feedback+ok; P2 clustered waiting. Skip ineligible.

**Step 2.** Read each eligible `<!-- MEMORY -->`. Verify named APIs still exist. Dedup against the target SKILL_MEMORY.

**Step 3.** Each proposal: Append / Merge / Retire, target skill+file, full text with Anchors and Related, evidence timestamps + slugs, risk. Capacity 2000 words (SKILL_MEMORY / cross-cutting). Retire needs grep proving anchors are gone. Attribution: (1) whitelisted `skill:` field (2) anchors hit exactly one project skill (3) 1 and 2 disagree -> user pick (4) anchors hit >=2 project skills -> `.castflow-runtime/rules/cross-cutting.md` (5) none -> do not write, leave waiting. Never write `.claude/rules/` business rules. Never write GLOBAL, CLAUDE.md, hooks, or this skill.

**Step 4.** One proposal at a time. Rejection writes `EVOLVE_REJECTION`.

**Step 5.** Atomic write. Replace analyzed entries with `<!-- PROCESSED ts:... entries:N proposals:M -->`. Drop `.trace_lock` in finally.

No score calibration. If snapshots look noisy, tell the user it is a hook/config issue.
