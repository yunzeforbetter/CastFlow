## Scenario 1: A healthy skill stays unchanged

The user names an existing skill and asks for a long-task check.

The iteration guide's focus is not broken. Opened scripts still hold the recorded features. Calls that were not opened are marked unverified. There is no newly confirmed feature.

Do not write a candidate. Do not edit the target skill. A health check is not a reason to change it.

## Scenario 2: The locator file was deleted

The script named by `EXAMPLES.md` no longer exists. Find a candidate file from a Git rename record or a symbol search, open it, and confirm it holds the original feature.

After that confirmation, update the locator. If there is no trustworthy owner, delete the stale locator or propose a retirement candidate. Do not invent a path.

## Scenario 3: The call chain cannot be verified

The locator script is still there, but the called definition was not opened this pass, or the project was not run.

Record unverified. Do not write that the chain is broken, and do not write that it takes effect at runtime. If there is no verifiable gap, leave the target skill unchanged.

## Scenario 4: A generic skill has no extra gain

The current model can finish the target task without loading the skill. The old skill adds generic advice, does not improve the target result, and increases false recall.

The candidate deletes the redundant rules or retires the skill. A longer candidate is not an improvement.

## Scenario 5: Three baselines support an overwrite

Under the same current model, the same context, and frozen prompts, no skill, the old skill, and the candidate skill all actually run. The candidate improves the target result. Regression and boundaries are not worse. Harmful behavior in the old skill is removed.

Run `validate` first. After it passes, overwrite the target skill, then run `validate` and `sync`. Business scripts are unchanged. Temporary evidence goes in `.castflow-runtime/tmp/skill-doctor/<target-skill-name>/` and is deleted when the task ends.
