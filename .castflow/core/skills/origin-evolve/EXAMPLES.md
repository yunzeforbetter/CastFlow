# Origin Evolve - Examples

---

## Example 1: Trace Record Format

Description
Hook scripts automatically create trace records. AI supplements type and skills fields.

Format

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
- `status`: `pending` (unprocessed) or `processed` (already analyzed by evolve)
- `correction`: `_` (none), `auto:minor` / `auto:major` (Hook detected self-correction), `minor` / `major` (AI supplemented)
- `score`: five-dimensional significance score (F/D/K/S/E weighted sum, admission threshold 1.5)
- `edit_count`: total edit events in the session (high count indicates iterative/difficult work)
- `modules`: auto-inferred from file paths by Hook
- `type` and `skills`: supplemented by AI (may remain `_` / `[]` if not filled)

---

## Example 2: Correction Pattern Detection

Description
Evolve identifies recurring self-correction patterns across multiple traces.

Trace data (3 entries with correction signals)

```
Trace 12: correction: auto:minor, modules: [Building], edit_count: 8
  -> Repeated edits to BuildingFunc, OnDestroy cleanup added after initial omission
Trace 18: correction: auto:minor, modules: [NPC], edit_count: 6
  -> NpcController missing Unsubscribe, corrected after first attempt
Trace 23: correction: auto:major, modules: [Building], edit_count: 12
  -> WorkerComponent timer cleanup iterated 4 times before correct
```

Analysis output

```
Pattern: OnDestroy resource cleanup omission
Evidence: 3 traces with correction signals, all involving Subscribe/Timer/Asset cleanup
Affected modules: Building (2x), NPC (1x)
Consistency: High (same root cause across modules)

Proposal:
  Type: SKILL_MEMORY entry
  Target: architect-skill/SKILL_MEMORY.md (cross-module architectural rule)
  Content: "All MonoBehaviour subclasses that use Subscribe, AddTimer,
           or LoadAsset must implement OnDestroy with corresponding
           Unsubscribe, RemoveTimer, or Release calls."
  Expected benefit: Reduce self-correction rate by ~15%
  Risk: Low (defensive rule, no false positive risk)
  Confidence: 0.9
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

Analysis output

```
Pattern: Navigation/pathfinding tasks have no dedicated skill coverage
Evidence: 3 bugfix tasks in RPGExplore/NPC modules, 2 with no skill match
Related existing skill: programmer-npc-skill (partial overlap)

Proposal:
  Type: Skill metadata update
  Target: programmer-npc-skill/SKILL.md
  Content: Add keywords "pathfinding, navigation, NavMesh, terrain"
           to metadata so these tasks auto-match
  Alternative: Create new navigation-skill if the domain grows
  Expected benefit: Future pathfinding tasks auto-match to programmer-npc-skill
  Risk: Low (metadata only, no content change)
  Confidence: 0.85
```

---

## Example 4: Append Operation

Description
User approves a new SKILL_MEMORY entry. Evolve appends with Anchors and Related fields.

Before (architect-skill/SKILL_MEMORY.md, last entry)

```markdown
### Rule 5: Event-driven communication

Anchors: [EventManager, Subscribe, Publish]
Related: Rule 3

...existing content...
```

After (appended at end of file)

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

Key constraints
- New entries must include Anchors (code symbols) and Related (cross-references)
- Follow the target file's existing numbering and heading style
- Content must be factual (derived from trace evidence)

---

## Example 5: Cross-Cutting Rule Creation

Description
A pattern spans multiple skills and has no natural home in any single SKILL_MEMORY.

Trace data

```
Trace 30: correction: auto:minor, modules: [Building, NPC], edit_count: 10, score: 3.50
Trace 35: correction: auto:major, modules: [Building, NPC], edit_count: 15, score: 3.97
Trace 41: correction: auto:minor, modules: [Building, NPC], edit_count: 8, score: 3.50
```

Analysis output

```
Pattern: WorkerSlot update order dependency between Building and NPC modules
Evidence: 3 traces with correction signals, all involving [Building, NPC] module pair
edit_count consistently high (8-15), indicating iterative debugging

Proposal:
  Type: Cross-cutting rule
  Target: .claude/rules/worker-slot-update-order.md
  Content: (see below)
  Expected benefit: Eliminate cross-module data race on WorkerSlot
  Risk: Low (ordering constraint, does not change logic)
  Confidence: 0.88
```

Generated rule file

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

---

## Example 6: Proposal Rejection Handling

Description
User rejects a proposal. Evolve records the reason to avoid repeating.

Interaction

```
Evolve: Proposal - Add rule "always use StringBuilder for 3+ concatenations"
        Evidence: 2 traces with string concat in hot path
        Confidence: 0.7

User: Reject. This is too aggressive, only matters in Update loops.

Evolve: Recorded. Will not re-propose this pattern unless evidence
        specifically involves Update/LateUpdate hot paths.
```

The rejection reason is appended to `.claude/traces/trace.md` as a meta-entry:

```markdown
<!-- EVOLVE_REJECTION -->
pattern: string-concatenation-rule
reason: User considers it too aggressive for general code, only relevant in Update loops
effect: Future proposals about string concat must be scoped to hot path contexts
<!-- /EVOLVE_REJECTION -->
```

---

## Example 7: Complexity Concentration Detection

Description
Evolve identifies files that are repeatedly iterated on, suggesting missing guidance.

Trace data

```
Trace 08: modules: [Building], edit_count: 14, file_count: 1, score: 1.88
  -> files: BuildingUpgradeFunc.cs
Trace 16: modules: [Building], edit_count: 11, file_count: 2, score: 2.33
  -> files: BuildingUpgradeFunc.cs, BuildingManager.cs
Trace 29: modules: [Building], edit_count: 9, file_count: 1, score: 1.78
  -> files: BuildingUpgradeFunc.cs
```

Analysis output

```
Pattern: BuildingUpgradeFunc.cs appears in 3 traces with consistently high edit_count (9-14)
Evidence: File is repeatedly iterated on, suggesting AI lacks clear usage rules for this class
Related skill: programmer-building-skill

Proposal:
  Type: EXAMPLES.md entry
  Target: programmer-building-skill/EXAMPLES.md
  Content: Add a representative code example showing the correct pattern
           for implementing BuildingUpgradeFunc subclass methods
  Expected benefit: Reduce edit iterations on BuildingFunc subclasses
  Risk: Low (additional example, no constraint change)
  Confidence: 0.82
```

---

## Example 8: Merge Operation

Description
Evolve discovers a new pattern that overlaps with an existing SKILL_MEMORY rule. Instead of appending a duplicate, it proposes merging.

Existing entry in programmer-building-skill/SKILL_MEMORY.md

```
### Rule 3: Resource cleanup in BuildingFunc

Anchors: [OnDestroy, Unsubscribe, RemoveTimer]
Related: Pitfall 2

Definition
BuildingFunc subclasses must clean up subscriptions and timers in OnDestroy.

Check list
- [ ] OnDestroy calls Unsubscribe for all events
- [ ] OnDestroy calls RemoveTimer for all timers
```

New pattern from trace analysis

```
Pattern: BuildingFunc subclasses also need to release loaded assets in OnDestroy
Evidence: Trace 44 (correction: auto:minor), Trace 51 (correction: auto:minor)
Both involved LoadAsset without matching Release in OnDestroy
```

Proposal (Merge, not Append)

```
Operation: Merge into existing Rule 3
Target: programmer-building-skill/SKILL_MEMORY.md

Diff:
  ### Rule 3: Resource cleanup in BuildingFunc
  
- Anchors: [OnDestroy, Unsubscribe, RemoveTimer]
+ Anchors: [OnDestroy, Unsubscribe, RemoveTimer, LoadAsset, Release]
  Related: Pitfall 2
  
  Definition
- BuildingFunc subclasses must clean up subscriptions and timers in OnDestroy.
+ BuildingFunc subclasses must clean up subscriptions, timers, and loaded assets in OnDestroy.
  
  Check list
  - [ ] OnDestroy calls Unsubscribe for all events
  - [ ] OnDestroy calls RemoveTimer for all timers
+ - [ ] OnDestroy calls Release for all LoadAsset handles

Rationale: Same rule, same code area. Adding a new Rule 10 would be redundant.
```

---

## Example 9: Retire Operation with Capacity Governance

Description
SKILL_MEMORY.md is approaching the 2000-word warning threshold. Evolve needs to add a new rule but first retires an obsolete entry.

Capacity check

```
Current: programmer-building-skill/SKILL_MEMORY.md = 1850 words
Proposed new entry: ~150 words
After append: 2000 words (at warning threshold)

Action: Find Retire candidates before Append
```

Anchor verification (grep results)

```
Rule 7: Building queue capacity check
  Anchors: [QueueCapacity, CheckQueueFull, MaxQueueSize]
  
  grep results:
    QueueCapacity -> 0 matches in project
    CheckQueueFull -> 0 matches in project
    MaxQueueSize -> 0 matches in project
  
  Verdict: All anchors missing. Queue system was refactored to use IQueueManager.
           Rule 7 is eligible for retirement.
```

Proposal (Retire + Append)

```
Proposal 1/2: Retire Rule 7
  Operation: Retire
  Target: programmer-building-skill/SKILL_MEMORY.md
  Reason: All 3 anchors (QueueCapacity, CheckQueueFull, MaxQueueSize) no longer exist
  Action: Change heading to "### Rule 7: Building queue capacity check [RETIRED]"
  Effect: -120 words effective (entry stays but AI skips it)

Proposal 2/2: Append Rule 10
  Operation: Append
  Target: programmer-building-skill/SKILL_MEMORY.md
  Content: (new rule with Anchors and Related)
  After both operations: ~1880 words (within recommended range)
```
