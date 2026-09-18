---
name: architect-skill
description: >
  Project architecture constraints and layering. Use when the user asks
  which layer a change belongs in, or whether it violates architecture.
  NOT module API how-to (programmer-*-skill).
---

# Architect-Skill

This project's architecture constraints and proven patterns. Query it before placing new systems.

## Yield

- How to call a module API -> that **programmer-*-skill**
- Where a bug is / null / race -> **debug-skill**
- Frame time / GC / allocation -> **profiler-skill**
- Creating this skill from catalog -> **skill-creator**

## Two roles

Constraint (must follow): hard rules in SKILL_MEMORY.md, examples in EXAMPLES.md Part 1.

Guide (reference): patterns in EXAMPLES.md Part 2-3. Do not treat a pattern as mandatory if it is not in SKILL_MEMORY.

## Duties

- Hard rules and traps -> SKILL_MEMORY.md
- Constraint cheat sheet and code -> EXAMPLES.md Part 1
- Pattern samples -> EXAMPLES.md Part 2-3

Before any architecture call: recon this repo's real layers and Manager/Service names (EXAMPLES + grep). Do not import patterns the codebase does not use.

## Nav

| Need | File |
|------|------|
| Patterns and code | EXAMPLES.md |
| Hard rules | SKILL_MEMORY.md |
| When to iterate | ITERATION_GUIDE.md |
