This file says when to change skill-doctor. It does not say how to edit a business module.

## What counts as an improvement changed

Trigger: the user changed the three baselines, the improvement bar, or an eval dimension that may change the verdict.

Edit: Rule 4 and Rule 5 in `SKILL_MEMORY.md`, and the flow in `SKILL.md`. If both files state the same verdict, change them together. Do not let them disagree.

Check: an improvement still requires the candidate to beat the old skill on results, with regression and boundaries no worse. If the old skill is harmful, restoring the current model's no-skill baseline and removing the harm also counts.

## Allowed write scope changed

Trigger: the user allows or forbids edits to business scripts, or the evidence directory must move.

Edit: the duties in `SKILL.md`, and Rule 1 in `SKILL_MEMORY.md`.

Check: business scripts stay read-only. The candidate and the evidence still land first in `.castflow-runtime/tmp/skill-doctor/<target-skill-name>/`. Do not write a maintenance queue, a hash, or Git-tracked state.

## Stale-locator classification changed

Trigger: the user changed how a missing file, a moved feature, an unproven call chain, or runtime evidence is judged.

Edit: duties 3 and 7 in `SKILL.md`, Rule 3 and Pitfall 3 in `SKILL_MEMORY.md`, and scenarios 2 and 3 in `EXAMPLES.md`.

Check: update a locator only after opening the new file and confirming the feature moved. A definition that was not opened is still unverified.

## Current-model baseline changed

Trigger: the executing model changed, or the user changed how no skill, the old skill, and the candidate skill are compared.

Edit: duties 6 and 8 in `SKILL.md`, Rule 4, Rule 5, and Rule 6 in `SKILL_MEMORY.md`, and scenarios 4 and 5 in `EXAMPLES.md`.

Check: the three eval groups use the same current model. After a model change, do not reuse old results. With no gain over the current model's no-skill baseline, a generic skill shrinks or retires.
