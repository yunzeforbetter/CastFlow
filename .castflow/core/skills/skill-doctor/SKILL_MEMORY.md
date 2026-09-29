### Rule 1: Edit the skill only, not project content

Anchors: [pattern:castflow-skills]
Related: Rule 4, Pitfall 1

Definition
The optimization only reads business scripts, prefabs, assets, and adapter mirrors. The candidate, snapshot, prompts, and results go in `.castflow-runtime/tmp/skill-doctor/<target-skill-name>/`. Overwrite the target skill's role files only after the verdict passes and `validate` passes. Do not write a maintenance queue, a hash, or a project business file.

Check list
- [ ] Business scripts and assets were not modified
- [ ] The candidate was not written into the target skill early
- [ ] Temporary evidence did not enter a Git-tracked file

### Rule 2: Fix the focus and the evidence scope first

Anchors: [pattern:ITERATION_GUIDE.md]
Related: Rule 3, Pitfall 2

Definition
Read the target skill's `SKILL.md` and `ITERATION_GUIDE.md` first. Stop if the guide is missing or cannot give a focus that can be checked. Read only the scripts it names, and the called definitions this pass actually opened. Every conclusion names the files that were opened. A definition that was not opened is unverified.

Check list
- [ ] Every gap points back to a guide focus or a new feature opened this pass
- [ ] An unverified item was not written as a break or as a runtime effect

### Rule 3: Classify a stale locator and a broken chain

Anchors: [pattern:EXAMPLES.md]
Related: Rule 2, Pitfall 3

Definition
A missing file, a moved feature, a missing called definition, and an unverified runtime are different states. Mark a locator stale only when the file is missing. Update a locator for a moved feature only after the new file is opened and confirmed. If the definition was not opened, mark it unverified. If the project was not run, do not write a runtime effect. If there is no trustworthy new owner, delete the stale claim or propose a retirement candidate. Do not invent a path.

Check list
- [ ] Every locator points at a real script
- [ ] A path after a move was opened and confirmed to hold the feature
- [ ] A runtime conclusion has an actual run as evidence

### Rule 4: Freeze the three eval groups before a candidate exists

Anchors: [pattern:skill-doctor]
Related: Rule 5, Pitfall 4

Definition
Freeze the prompts before the candidate body is written. Run no skill, the old skill, and the candidate skill with the same current model and the same context. Prompts include at least the target task and an adjacent or out-of-scope task. If a locator is stale, add a moved or missing scenario. Without an actual run, do not claim a result.

Check list
- [ ] Prompts exist before the candidate body
- [ ] The three groups use the same current model
- [ ] Results, regression, recall, and out-of-scope behavior all have evidence

### Rule 5: Write back only an evidenced improvement

Anchors: [pattern:SKILL.md]
Related: Rule 1, Rule 4, Pitfall 1, Pitfall 5

Definition
The candidate must have a citable advantage over the old skill on the target result. Regression and boundaries must not be worse. If the old skill is clearly harmful, a candidate that restores the no-skill baseline and removes the harm also counts as an improvement. A generic skill that does not beat the current model's no-skill result shrinks, retires, or is deleted. No change, a downgrade, a mixed result, or no difference does not overwrite. Run `validate` before and after the overwrite. After it passes, run `sync`.

Check list
- [ ] When the verdict is not an improvement, the target skill stays as it was
- [ ] A reading step or a single stable run was not treated as a quality gain
- [ ] The overwritten skill passes `validate` again

### Rule 6: The current model is the capability baseline

Anchors: [pattern:current-model]
Related: Rule 4, Pitfall 6

Definition
Eval uses the model executing the task as the highest capability baseline. Do not compare against a weaker or historical model. If the model changes during one comparison, discard the results and rerun. A skill keeps only project facts, boundaries, and operating constraints that the current model cannot infer reliably. Delete general knowledge and steps the model already performs reliably.

Check list
- [ ] The no-skill baseline uses the current model
- [ ] The candidate does not copy generic advice the model already follows
- [ ] After a model change, old conclusions were not reused

### Pitfall 1: Edited the body without an improvement

Anchors: [pattern:SKILL.md]
Related: Rule 5

Symptom
The gap looked plausible, so the target skill's files were edited.

Guard
Compare first, then write. No difference means leave the original files.

### Pitfall 2: Widening the scan to the whole repo

Anchors: [pattern:EXAMPLES.md]
Related: Rule 2, Rule 4

Symptom
Looking for more content opens unrelated modules and adds new duties to the skill.

Guard
Scope comes only from the guide, the named scripts, and the called definitions opened this pass.

### Pitfall 3: Writing unverified as failed

Anchors: [pattern:EXAMPLES.md]
Related: Rule 3

Symptom
The callee was not opened, or the project was not run, yet the chain is asserted broken or effective at runtime.

Guard
Use unverified. A stronger conclusion needs a missing file, a confirmed move, or an actual run.

### Pitfall 4: Writing prompts after seeing the candidate

Anchors: [pattern:skill-doctor]
Related: Rule 4

Symptom
Eval prompts follow the candidate's wording, so the result favors the candidate.

Guard
Freeze the prompts before the candidate. Prompts state results and constraints only.

### Pitfall 5: Treating generic advice as a capability gain

Anchors: [pattern:current-model]
Related: Rule 5, Rule 6

Symptom
The candidate adds "analyze carefully, work step by step, check the result" and other steps the current model already takes.

Guard
Compare against the current model's no-skill baseline. No extra gain means shrink or retire.

### Pitfall 6: Using a model-version gap as a verdict

Anchors: [pattern:current-model]
Related: Rule 4

Symptom
A difference between an old model and the current model is misread as a skill improvement.

Guard
The three eval groups use the same current model. After a model change, rerun all of them.
