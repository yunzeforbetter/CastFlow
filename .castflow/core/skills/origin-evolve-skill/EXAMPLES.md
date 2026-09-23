# Origin Evolve - Examples

These are proposal shapes for schema:4 memory snapshots. They are not a second copy of the rules.

## Example 1: One ok feedback is enough to propose

A single `feedback` snapshot with `quality: ok` names a missing cleanup. Homology is not required for this type.

```markdown
<!-- MEMORY skill:programmer-building-skill quality:ok -->
BuildingFunc.OnDestroy drops the Subscribe but not the AddTimer.
Anchors: Subscribe, AddTimer, OnDestroy
<!-- /MEMORY -->
```

```text
Operation:   Append
Target:      programmer-building-skill/SKILL_MEMORY.md
Evidence:    that snapshot's timestamp
Content:     MonoBehaviour subclasses that Subscribe, AddTimer, or LoadAsset
             must OnDestroy with Unsubscribe, RemoveTimer, or Release.
Anchors:     [method:Building/BuildingFunc:OnDestroy, pattern:AddTimer]
Related:     Rule 5
```

A `project` or `reference` snapshot with the same text stays waiting until `manager.py homology` puts it in a component of size >= 2. Do not compute Jaccard by hand, and do not spawn one Python process per pair.

## Example 2: Two skills, one cross-cutting file

Anchors hit both `programmer-building-skill` and `programmer-npc-skill`, and the whitelisted `skill:` field does not pick one of them. Rule 2 step 4 applies. Write `.castflow-runtime/rules/cross-cutting.md`. Do not write `.claude/rules/`.

```markdown
# Worker slot update order

When building-system and npc-system both change WorkerSlot in one operation,
building-side updates finish before NPC-side reads or writes.
```

When both anchors hit exactly one project skill, write that skill instead:

```markdown
### Rule 6: OnDestroy resource cleanup

Anchors: [method:Building/BuildingFunc:OnDestroy, pattern:Subscribe, pattern:AddTimer]
Related: Rule 5

Definition
A MonoBehaviour that uses Subscribe, AddTimer, or LoadAsset implements OnDestroy
with Unsubscribe, RemoveTimer, or Release.

Check list
- [ ] Subscribe -> OnDestroy has Unsubscribe
- [ ] AddTimer -> OnDestroy has RemoveTimer
- [ ] LoadAsset -> OnDestroy has Release
```

Every new SKILL_MEMORY entry has both `Anchors:` and `Related:`.

## Example 3: Merge, and retire before the word cap

The new pattern is the same code area as an existing rule. Homology reports Jaccard >= 0.5 against Rule 3, so this is a Merge, not an Append.

```text
Operation: Merge into Rule 3
Target:    programmer-building-skill/SKILL_MEMORY.md

Diff:
  ### Rule 3: Resource cleanup in BuildingFunc

- Anchors: [OnDestroy, Unsubscribe, RemoveTimer]
+ Anchors: [method:Building/BuildingFunc:OnDestroy, pattern:Unsubscribe, pattern:RemoveTimer, pattern:LoadAsset, pattern:Release]

  Definition
- BuildingFunc subclasses clean up subscriptions and timers in OnDestroy.
+ BuildingFunc subclasses clean up subscriptions, timers, and loaded assets in OnDestroy.

  Check list
  - [ ] OnDestroy calls Unsubscribe for every subscription
  - [ ] OnDestroy calls RemoveTimer for every timer
+ - [ ] OnDestroy calls Release for every LoadAsset handle
```

If the file is already near the 2000-word cap, retire an obsolete entry first:

```text
Current: programmer-building-skill/SKILL_MEMORY.md = 1850 words
Proposed merge delta: ~150 words, which would cross 2000

Retire candidate - Rule 7: Building queue capacity check
  Anchors: [QueueCapacity, CheckQueueFull, MaxQueueSize]
  grep: all 3 anchors -> 0 matches (queue moved to IQueueManager)
  Action: prepend [RETIRED] to the heading. Do not delete the body.
  Effect: -120 effective words

Combined: Retire Rule 7 (-120) + Merge (+150) -> about 1880 words
```

Show that diff at Step 4. Do not write it before the user accepts.

## Example 4: Rejection stops the same pattern

```markdown
<!-- EVOLVE_REJECTION -->
pattern: string-concatenation-rule
reason: User considers it too broad; it applies only inside Update loops
effect: A later string-concat proposal must be scoped to a hot path
<!-- /EVOLVE_REJECTION -->
```

Read existing rejections before proposing. A rejected pattern is not proposed again outside the scope the rejection recorded.
