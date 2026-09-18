---
name: profiler-skill
description: >
  Hot-path performance review for this repo. Use when a hot path is
  slow, hitching, or allocating. NOT functional bugs (debug-skill).
---

# Profiler-Skill

Performance guard: find costly patterns in real hot paths, not generic advice.

## Yield

- Wrong layer / cyclic deps -> **architect-skill**
- Crash / null / race correctness -> **debug-skill**
- How to call a module API -> that **programmer-*-skill**

## Duties

1. Hot path: repeated lookup, virtual churn, sync IO on the main thread
2. Allocation: per-frame / per-request temps
3. Leak: subscriptions, caches, unbounded queues
4. Report: site, why it costs, cheaper option, expected gain

## L1 knobs (ask if missing, then proceed)

- target_platform: Mobile / PC / Server / Web
- optimization_goal: Battery / HighPerformance / MemorySavings
- check_depth: Audit (patterns) / DeepScan (line-level)

## Budget (L2)

{{PERFORMANCE_BUDGETS}}

## Matrix

| Class | Smell | Move | Effect |
|------|------|------|--------|
| Alloc | Temp objects on the hot path | Pool / reuse / prealloc | Less GC |
| CPU | Lookup inside a tight loop | Cache the ref | Lower cost per tick |
| Leak | Subscribe without unsubscribe | Pair add/remove | Stable RSS |
| Redundant | Recompute every tick | Dirty flag | Scales with N |

## Project extras

{{PROJECT_SPECIFIC_OPTIMIZATIONS}}

## Nav

| Need | File |
|------|------|
| Examples | EXAMPLES.md |
| Hard rules | SKILL_MEMORY.md |
| Iterate | ITERATION_GUIDE.md |
