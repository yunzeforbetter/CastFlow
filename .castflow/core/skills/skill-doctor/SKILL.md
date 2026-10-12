---
name: skill-doctor
description: >
  Evaluate and iterate an existing skill: fix stale locators and broken
  links, and shrink or raise rules against the current model. Use when
  the user asks to maintain an existing skill. NOT creating a new skill
  (skill-creator).
---

# skill-doctor

Finish "maintain an existing skill" in one pass. The goal is a skill with a provable gain on this project and the current model. The result may be a fix, a shrink, a retirement, a deletion, or no change.

## Yield

Creating a skill, or writing a programmer skill from the generation queue, yields to skill-creator. Compiling a requirement into a package and then stopping yields to goal-loop-creator. This skill runs the optimization itself.

## Duties

If the user did not name a target skill, ask. Do not scan the whole repo. Optimize one skill at a time. If `ITERATION_GUIDE.md` is missing, stop. Do not invent a focus.

1. Read the target skill's `SKILL.md` and `ITERATION_GUIDE.md`. Turn the guide's triggers into this pass's scope. If the scope is unclear, stop.
2. Read only the scripts the target skill names, and the definitions this pass actually opened on the call chain. Do not edit business scripts, prefabs, assets, or adapter mirrors.
3. Classify health first: locator ok, file missing, feature moved, call chain broken, rule stale, generic content with no gain, or skill harmful. A definition that was not opened is unverified. If the project was not run, do not claim a runtime effect.
4. Record the gap, or confirm there is none. A new feature may come only from a script opened this pass, and only if the target skill does not already record it. Do not invent a feature. Do not widen the module scope.
5. Freeze the eval prompts before any candidate body exists. Prompts state the finished result, the constraints, and the boundaries. They do not quote the candidate's wording. Put the temporary snapshot, prompts, candidate, and results in `.castflow-runtime/tmp/skill-doctor/<target-skill-name>/`. Do not write a maintenance queue, a hash, or Git-tracked state.
6. Run three groups with the same current model and the same context: no skill, old skill, and candidate skill. Cover at least one target task and one adjacent or out-of-scope task. If a call chain is broken, add a moved or missing scenario. Without an actual run, do not claim the eval passed.
7. The candidate writes only a fix that has evidence. Update a stale locator only after the new file is opened and confirmed. An uncertain chain stays unverified. A generic skill that does not beat the current model shrinks or retires.
8. Write back to the target skill only when the candidate has a citable advantage over the old skill on the target result, and regression, boundaries, and out-of-scope behavior are not worse. If the old skill is harmful, restoring the no-skill baseline and removing the harm also counts as an improvement. No change, a downgrade, a mixed result, or no difference: do not overwrite.
9. Run `py .castflow-runtime/manager.py validate` before and after the overwrite. After it passes, run `py .castflow-runtime/manager.py sync`. On failure, leave the original skill unchanged. Delete the temporary directory when the task ends, unless the user asks to keep the report.

Eval looks at results, regression, recall, out-of-scope behavior, and the no-skill baseline. Record stability and cost only. One run, or reading a few more files, is not an improvement. If the model changes during the task, discard the comparison and rerun with the current model.

The evidence directory is `.castflow-runtime/tmp/skill-doctor/<target-skill-name>/`. It is a temporary directory for one task. It is not project collaboration state, and it is not written into a maintenance queue.

## Read next

- Stale locators, moves, no gain, and improvement: `EXAMPLES.md`
- Evidence, the three baselines, and write bounds: `SKILL_MEMORY.md`
- When to rewrite this skill: `ITERATION_GUIDE.md`
