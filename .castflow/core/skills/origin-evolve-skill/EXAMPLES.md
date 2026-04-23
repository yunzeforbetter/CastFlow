# Origin Evolve - Examples

---

## Example 1: Correction Cluster + Complexity Concentration

Three traces over a week show repeated edits to the same file.

```
Trace 12: correction:auto:minor  modules:[Building]  edit_count:8
  -> BuildingFunc, OnDestroy cleanup added after initial omission
Trace 23: correction:auto:major  modules:[Building]  edit_count:12
  -> WorkerComponent timer cleanup iterated 4 times before correct
Trace 29: correction:_           modules:[Building]  edit_count:14  file_count:1
  -> BuildingUpgradeFunc.cs (same file in 3 traces with edit_count 9-14)
```

Two patterns, two proposals.

```
Pattern A: OnDestroy resource cleanup omission
  Evidence:    Trace 12 + Trace 23 (correction signals on Subscribe/Timer cleanup)
  Operation:   Append
  Target:      programmer-building-skill/SKILL_MEMORY.md
  Content:     "MonoBehaviour subclasses using Subscribe / AddTimer / LoadAsset
                must implement OnDestroy with corresponding Unsubscribe / RemoveTimer / Release."
  Anchors:     [Subscribe, Unsubscribe, AddTimer, RemoveTimer, LoadAsset, Release, OnDestroy]
  Related:     Rule 5
  Confidence:  0.9

Pattern B: BuildingUpgradeFunc complexity concentration
  Evidence:    Trace 12 + Trace 23 + Trace 29 (consistent high edit_count, low file_count)
  Operation:   Append (or Merge into nearest BuildingFunc example)
  Target:      programmer-building-skill/EXAMPLES.md
  Content:     Representative subclass implementation with cleanup contract
  Confidence:  0.82
```

Each proposal cites the exact trace timestamps. Step 4 surfaces both.

---

## Example 2: Append vs Cross-Cutting Routing

A proposal touches two modules with no common parent (Building under City, NPC under World). Per Rule 2, target is `.claude/rules/`, not either skill.

```markdown
# Worker Slot Update Order

When both building-system and npc-system modify WorkerSlot data
in the same operation, building-side updates must complete before
NPC-side reads or writes. This prevents data inconsistency where
NPC logic reads stale worker assignment data.

Affected scenarios:
- Building upgrade changing worker capacity
- Building destruction releasing workers
- Worker reassignment during building state changes
```

Single-skill alternative (when both modules share a parent skill):

```markdown
### Rule 6: OnDestroy resource cleanup

Anchors: [Subscribe, Unsubscribe, AddTimer, RemoveTimer, LoadAsset, Release, OnDestroy]
Related: Rule 5

All MonoBehaviour subclasses that use Subscribe, AddTimer, or LoadAsset
must implement OnDestroy with corresponding Unsubscribe, RemoveTimer, or Release.

Check list
- [ ] Subscribe -> OnDestroy has Unsubscribe
- [ ] AddTimer -> OnDestroy has RemoveTimer
- [ ] LoadAsset -> OnDestroy has Release
```

Required: every new SKILL_MEMORY entry has `Anchors:` and `Related:`.

---

## Example 3: Merge with Capacity Pressure (Append + Retire combined)

Existing rule covers a subset of the new pattern.

```
Operation: Merge into existing Rule 3
Target:    programmer-building-skill/SKILL_MEMORY.md

Diff:
  ### Rule 3: Resource cleanup in BuildingFunc

- Anchors: [OnDestroy, Unsubscribe, RemoveTimer]
+ Anchors: [OnDestroy, Unsubscribe, RemoveTimer, LoadAsset, Release]

  Definition
- BuildingFunc subclasses must clean up subscriptions and timers in OnDestroy.
+ BuildingFunc subclasses must clean up subscriptions, timers, and loaded assets in OnDestroy.

  Check list
  - [ ] OnDestroy calls Unsubscribe for all events
  - [ ] OnDestroy calls RemoveTimer for all timers
+ - [ ] OnDestroy calls Release for all LoadAsset handles

Rationale: same root cause, same code area; adding a separate rule would be redundant.
```

When the file is over the 2000-word capacity, retire an obsolete entry first:

```
Current: programmer-building-skill/SKILL_MEMORY.md = 1850 words
Proposed new entry: ~150 words -> would hit 2000-word threshold

Retire candidate - Rule 7: Building queue capacity check
  Anchors: [QueueCapacity, CheckQueueFull, MaxQueueSize]
  grep results: all 3 anchors -> 0 matches (queue system refactored to IQueueManager)
  Action: prepend [RETIRED] to heading; do NOT delete
  Effect: -120 effective words

Combined: Retire Rule 7 (-120) + Append (+150) -> ~1880 words (within capacity)
```

---

## Step 1 Diagnostic Output (Reference)

The three counts surface attribution and merge errors carried over from previous evolutions.

```
[diagnostic]
within-skill drift overlap pairs (Jaccard >= 0.5): 0
cross-skill identical anchor sets:                 0
cross-skill overlap pairs (Jaccard >= 0.5):        2
  - programmer-building-skill rule#3 <-> programmer-ui-skill rule#5  (Jaccard 0.62)
```

Non-zero counts feed Step 2: in this case, propose either Merge into one skill (if anchor evidence is dominant) or move both rules to `.claude/rules/` (if genuinely cross-cutting). Step 4 user approval still required.

---

## Rejection Format

Every rejected proposal records its scope to prevent re-proposal:

```markdown
<!-- EVOLVE_REJECTION -->
pattern: string-concatenation-rule
reason: User considers it too aggressive for general code, only relevant in Update loops
effect: Future proposals about string concat must be scoped to hot path contexts
<!-- /EVOLVE_REJECTION -->
```
