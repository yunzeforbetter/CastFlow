---
name: module-mark-skill
description: >
  Mark candidate packages before a module cut. Use when cold-start must
  separate a feature, a shared method, an independent system, and a
  framework mechanism. NOT a programmer skill for one module.
---

# Module marks

Mark packages so the module cut follows how this repo is built. The mark
is a weight on an engineering stance. It is not a directory rule and not a
skill.

## Yield

- One module's API how-to -> that `programmer-*-skill`
- Drawing the package graph or printing the first cut -> `coldstart`
- Designing a Jev question for some other job -> the `jev` skill, if installed
- Writing scan ledgers (`GRAPH.md`, `knowledge-graph.json`, `.ua/`) -> never

## Responsibilities

1. Build one evidence card per candidate package from the scanner. Do not
   invent packages by reading files one by one.
2. Score four stances: feature, shared method, independent system, framework
   mechanism. Use a structural prior always. When `TYPESAFE_API_KEY` is set,
   unresolved cards go to official TypeSafe System One (`jev-latest` unless
   `TYPESAFE_DEFAULT_MODEL` is set). When it is not set, say so and keep the
   prior. Do not invent a probability.
3. Turn the winning stance into `attach`, `split`, `keep`, or `review`.
   Show the revised cut. Do not hide unmarked rows.
4. Persist a mark only after the user accepts it. The next scan applies
   accepted marks before the prior and before Jev.

## Navigate

- EXAMPLES.md — evidence card, Jev questions, cut actions
- SKILL_MEMORY.md — what a mark is not allowed to do
- ITERATION_GUIDE.md — when this skill changes
- marks.schema.json — card and decision fields; read it when emitting marks
