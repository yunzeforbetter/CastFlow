# Origin Evolve - Examples

---

## Example 1: Trace Record Format

Description
code-pipeline Step 9 writes trace records in this format.

Format

```markdown
<!-- TRACE status:pending -->
task: Implement batch building upgrade with queue capacity check
skills: [building-system, queue-system]
sub_agents: 2 (building-logic, building-ui)
files_modified: [BuildingManager.cs, BuildingUpgradeFunc.cs, BatchUpgradePanel.cs]
retries: Step 3 retried once (compile error: missing using statement)
user_corrections: none
outcome: success
<!-- /TRACE -->
```

Key fields
- `status`: `pending` (unprocessed) or `processed` (already analyzed by evolve)
- `retries`: Which step retried and why (critical for failure pattern detection)
- `user_corrections`: Any mid-workflow corrections from user (critical for knowledge gap detection)

---

## Example 2: Failure Pattern Detection

Description
Evolve identifies a recurring retry pattern across multiple traces.

Trace data (3 entries showing same pattern)

```
Trace 12: retries: Step 3 retried (BuildingFunc subclass missing OnDestroy cleanup)
Trace 18: retries: Step 3 retried (NpcController missing Unsubscribe in OnDestroy)
Trace 23: retries: Step 5 NO-GO (WorkerComponent missing timer cleanup in OnDestroy)
```

Analysis output

```
Pattern: OnDestroy resource cleanup omission
Occurrences: 3 out of last 20 traces (15%)
Affected skills: building-system, npc-system
Consistency: High (same root cause each time)

Proposal:
  Type: SKILL_MEMORY entry
  Target: architect-skill/SKILL_MEMORY.md (cross-module architectural rule)
  Content: "All MonoBehaviour subclasses that use Subscribe, AddTimer,
           or LoadAsset must implement OnDestroy with corresponding
           Unsubscribe, RemoveTimer, or Release calls."
  Expected benefit: Reduce retry rate by ~15%
  Risk: Low (defensive rule, no false positive risk)
  Confidence: 0.9
```

---

## Example 3: Knowledge Gap Detection

Description
Evolve identifies tasks that failed to match any skill.

Trace data

```
Trace 15: skills: [] (no skill matched), task: "fix pathfinding stuck on slopes"
Trace 19: skills: [] (no skill matched), task: "NPC gets stuck on terrain edges"
Trace 22: skills: [npc-system] (partial match), task: "navigation mesh hole near buildings"
```

Analysis output

```
Pattern: Navigation/pathfinding tasks have no dedicated skill coverage
Occurrences: 3 tasks with no or partial match
Related existing skill: npc-system (partial overlap)

Proposal:
  Type: Skill metadata update
  Target: npc-system/SKILL.md
  Content: Add keywords "pathfinding, navigation, NavMesh, terrain"
           to metadata so these tasks match npc-system
  Alternative: Create new navigation-skill if the domain grows
  Expected benefit: Future pathfinding tasks auto-match to npc-system
  Risk: Low (metadata only, no content change)
  Confidence: 0.85
```

---

## Example 4: Applying an Approved Proposal

Description
User approves a SKILL_MEMORY entry proposal. Evolve appends it correctly.

Before (architect-skill/SKILL_MEMORY.md, last entry)

```markdown
### Rule 5: Event-driven communication

...existing content...
```

After (appended at end of file)

```markdown

---

### Rule 6: OnDestroy resource cleanup

**Definition**: All MonoBehaviour subclasses that use Subscribe, AddTimer, or LoadAsset must implement OnDestroy with corresponding Unsubscribe, RemoveTimer, or Release calls.

**Check list**:
- [ ] Does the class call Subscribe? If yes, OnDestroy must have Unsubscribe
- [ ] Does the class call AddTimer? If yes, OnDestroy must have RemoveTimer
- [ ] Does the class call LoadAsset? If yes, OnDestroy must have Release
```

Key constraints
- Append only, never modify existing entries
- Follow the target file's existing format (rule numbering, heading style)
- Content must be factual (derived from trace evidence, not speculative)

---

## Example 5: Cross-Cutting Rule Creation

Description
A pattern spans multiple skills and has no natural home in any single SKILL_MEMORY.

Trace data

```
Trace 30: retries: Step 4 SignatureMismatch (building and NPC both modify WorkerSlot)
Trace 35: user_corrections: "building side must update WorkerSlot before NPC reads it"
Trace 41: retries: Step 3 retried (race condition on WorkerSlot between modules)
```

Analysis output

```
Pattern: WorkerSlot update order dependency between building and NPC systems
Occurrences: 3 across building-system and npc-system
No single skill owns this rule

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
Evolve: Proposal - Add rule "always use StringBulder for 3+ concatenations"
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
