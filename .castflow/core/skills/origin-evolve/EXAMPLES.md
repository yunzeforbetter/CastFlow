# Origin Evolve - Examples

---

## Example 1: Trace Record Format and Rejection

Description
Hook scripts create trace records; AI supplements type/skills. User rejections are recorded as EVOLVE_REJECTION entries.

Trace format

```markdown
<!-- TRACE status:pending -->
timestamp: 2026-04-13T10:00:00Z
type: feature
correction: auto:minor
modules: [Building, Queue]
skills: [programmer-building-skill]
files_modified: [BuildingManager.cs, BuildingUpgradeFunc.cs, BatchUpgradePanel.cs]
file_count: 3
lines_changed: 80
edit_count: 12
score: 3.50
<!-- /TRACE -->
```

Key fields
- `status`: `pending` (unprocessed) or `processed` (analyzed)
- `correction`: `_` (none), `auto:minor`/`auto:major` (Hook-detected), `minor`/`major` (AI-supplied)
- `score`: five-dimensional weighted sum (threshold 1.5)
- `edit_count`: total edits in session (high = difficult work)

Rejection format

```markdown
<!-- EVOLVE_REJECTION -->
pattern: string-concatenation-rule
reason: User considers it too aggressive for general code, only relevant in Update loops
effect: Future proposals about string concat must be scoped to hot path contexts
<!-- /EVOLVE_REJECTION -->
```

---

## Example 2: Correction Pattern and Complexity Detection

Description
Evolve identifies recurring self-correction patterns and files with consistently high edit iterations.

Trace data

```
Trace 12: correction: auto:minor, modules: [Building], edit_count: 8
  -> Repeated edits to BuildingFunc, OnDestroy cleanup added after initial omission
Trace 23: correction: auto:major, modules: [Building], edit_count: 12
  -> WorkerComponent timer cleanup iterated 4 times before correct
Trace 29: correction: _, modules: [Building], edit_count: 14, file_count: 1
  -> files: BuildingUpgradeFunc.cs (same file in 3 traces with edit_count 9-14)
```

Analysis output

```
Pattern 1: OnDestroy resource cleanup omission
  Evidence: 2 traces with correction signals, both involving Subscribe/Timer cleanup
  Proposal: SKILL_MEMORY entry in architect-skill
  Content: "MonoBehaviour subclasses using Subscribe/AddTimer/LoadAsset must implement
           OnDestroy with corresponding Unsubscribe/RemoveTimer/Release"
  Confidence: 0.9

Pattern 2: BuildingUpgradeFunc.cs complexity concentration
  Evidence: 3 traces, consistently high edit_count (9-14), low file_count
  Proposal: EXAMPLES.md entry in programmer-building-skill
  Content: Add representative code example for BuildingUpgradeFunc subclass methods
  Confidence: 0.82
```

---

## Example 3: Knowledge Gap Detection

Description
Evolve identifies tasks where no skill was matched.

Trace data

```
Trace 15: skills: [], modules: [RPGExplore], type: bugfix, score: 2.33
Trace 19: skills: [], modules: [NPC], type: bugfix, score: 2.68
Trace 22: skills: [programmer-npc-skill], modules: [NPC, Building], type: bugfix, score: 3.12
```

Proposal

```
Type: Skill metadata update
Target: programmer-npc-skill/SKILL.md
Content: Add keywords "pathfinding, navigation, NavMesh, terrain" to metadata
Alternative: Create new navigation-skill if domain grows
Confidence: 0.85
```

---

## Example 4: Append and Cross-Cutting Rule

Description
Append adds new entries with Anchors/Related fields. Cross-cutting patterns (spanning multiple skills) go to `.claude/rules/`.

Single-skill Append (after architect-skill/SKILL_MEMORY.md Rule 5)

```markdown

---

### Rule 6: OnDestroy resource cleanup

Anchors: [Subscribe, Unsubscribe, AddTimer, RemoveTimer, LoadAsset, Release, OnDestroy]
Related: Rule 5

Definition
All MonoBehaviour subclasses that use Subscribe, AddTimer, or LoadAsset must implement OnDestroy with corresponding Unsubscribe, RemoveTimer, or Release calls.

Check list
- [ ] Does the class call Subscribe? If yes, OnDestroy must have Unsubscribe
- [ ] Does the class call AddTimer? If yes, OnDestroy must have RemoveTimer
- [ ] Does the class call LoadAsset? If yes, OnDestroy must have Release
```

Cross-cutting rule (2+ modules, no common parent -> `.claude/rules/`)

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

Key constraints
- New entries must include Anchors (code symbols) and Related (cross-references)
- Follow the target file's existing numbering and heading style
- Cross-module patterns without a common parent go to `.claude/rules/`

---

## Example 5: Merge and Retire with Capacity Governance

Description
Merge expands existing entries when patterns overlap. Retire marks obsolete entries when anchors no longer exist in code. Both may happen together for capacity management.

Merge scenario (existing Rule 3 + new LoadAsset pattern)

```
Operation: Merge into existing Rule 3
Target: programmer-building-skill/SKILL_MEMORY.md

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

Rationale: Same rule, same code area. Adding a new Rule 10 would be redundant.
```

Retire scenario (anchors missing from codebase, with capacity pressure)

```
Current: programmer-building-skill/SKILL_MEMORY.md = 1850 words
Proposed new entry: ~150 words -> would hit 2000-word threshold

Retire candidate - Rule 7: Building queue capacity check
  Anchors: [QueueCapacity, CheckQueueFull, MaxQueueSize]
  grep results: all 3 anchors -> 0 matches (queue system refactored to IQueueManager)
  Action: Add [RETIRED] to heading (do NOT delete)
  Effect: -120 words effective

Combined: Retire Rule 7 (-120) + Append Rule 10 (+150) -> ~1880 words (within range)
```
