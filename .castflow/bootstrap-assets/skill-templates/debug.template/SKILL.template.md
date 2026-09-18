---
name: debug-skill
description: >
  Boundary and failure inspection for this repo. Use when diagnosing
  null, race, or crash failures. NOT module API how-to (programmer-*-skill).
---

# Debug-Skill

Quality guard: verify code under empty, null, destroyed, concurrent, and integration edges.

## Yield

- Architecture / which layer -> **architect-skill**
- Perf / allocation / hot path -> **profiler-skill**
- How a module API is supposed to work -> that **programmer-*-skill**

## Duties

1. Data edges: null, empty collections, index, overflow
2. Lifecycle: init order, dispose, re-entry
3. Integration: timeouts, config missing, event re-entrancy
4. Report: failing check, evidence, suggested patch (if asked)

## Depth (pick one, default Focused)

- Deep: full checklist, core logic
- Focused: data edges + state transitions
- Quick: P0 null/empty only

focus_area: {{FOCUS_AREAS}}

## Checklist

### Data
- [ ] Member access has null guards
- [ ] Iterate only when Count > 0
- [ ] Index in [0, Count-1]
- [ ] Numeric Min/Max
- [ ] Empty string vs null
- [ ] 0/null not treated as a valid domain value by accident
- [ ] Dict lookup is safe
- [ ] Type casts checked

### State
- [ ] Method preconditions (initialized)
- [ ] Shutdown releases subscriptions/handles
- [ ] No use-after-destroy
- [ ] Shared state guarded if concurrent
- [ ] Init -> Execute -> Close order

### Integration
- [ ] Args match real signatures (grep)
- [ ] Async has timeout
- [ ] Config keys exist before read
- [ ] Handlers do not re-fire the same event unbounded

## Project extras

{{PROJECT_SPECIFIC_CHECKS}}

## Nav

| Need | File |
|------|------|
| Worked examples | EXAMPLES.md |
| Hard rules | SKILL_MEMORY.md |
| Iterate | ITERATION_GUIDE.md |
