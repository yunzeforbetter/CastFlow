---
name: skill-iteration
description: >
  CastFlow four-file skill format. Use only when creating or restructuring
  a skill, or when skill-creator asks for the format. NOT for implementing
  features.
---

# SKILL_ITERATION.md

Shape of a skill file. Load only at **T4-MAINTAIN** (create a skill, or change its structure). Calling a skill to write code is `GLOBAL_SKILL_MEMORY.md` and the project `CLAUDE.md`, not here.

Write a new project skill, and a later evolve update of that skill, under `castflow-skills/<name>/`. Do not write that body under `.castflow-runtime/skills/` — a full cold start deletes that tree and recopies factory skills. Do not write a factory-owned name (`skill-creator`, `goal-loop-creator`, `origin-evolve-skill`) into `castflow-skills/`; that directory is ignored for those names. Do not write adapter mirrors. `python .castflow-runtime/manager.py sync` projects each skill once onto `.claude/skills` and `.agents/skills`. Do not create `.grok/skills` or `.cursor/skills` (compatibility residue; sync deletes them so they are not scanned twice).

A `programmer-*-skill` follows this file only. No domain README, no `*.template.md`. Architect / debug / profiler recall sentences are below; their bodies still follow this file. If one role file contains both `{{` and `}}`, validate fails it as a leftover placeholder. The check is a raw substring, not a token shape. If copied sample code contains that pair, rewrite the sample.

An orchestration doc passes a skill name, a scope, and paths. It does not copy this file.

This file constrains **catalog and module skills**. Agents, this file, and freeform eval attachments have their own shapes.

Check: `python .castflow-runtime/manager.py validate`. A directory is a catalog skill when it has `SKILL.md` and every markdown file is one of `SKILL.md`, `EXAMPLES.md`, `SKILL_MEMORY.md`, `ITERATION_GUIDE.md`, or when a catalog skill also contains another markdown file. A `programmer-*-skill` has `SKILL.md` and `ITERATION_GUIDE.md`. `EXAMPLES.md` is created only when a feature is located in a script file. `SKILL_MEMORY.md` is created only when a rule exists, including an implicit rule or a convention. An empty or heading-only `EXAMPLES.md` or `SKILL_MEMORY.md` is an **error** (delete it). A heading with no entry is not empty. It is a stub, and validate fails it. Any other catalog skill may omit a role file it has no job for. A present empty or heading-only role file on that other skill is an **error** (delete it). Another markdown file on a catalog skill is an **error**. A non-markdown attachment with no pointer from a present role file is an **error**. Bad description shape, `{{` plus `}}` in one file, or emoji is an **error**. A directory whose markdown is outside that set (no `SKILL.md`, or only nested markdown such as skill-creator) is skipped, not failed. Over the size cap is a **warning**, not permission to open another file.

## Prose language

Generated skill prose uses the cold-start choice. Read `language` on the queue card, otherwise `.castflow-runtime/config.json` key `language`. Missing, empty, or `en` means English. `zh` means Chinese. Any other code means that language. Default is English. Do not switch because repo comments are in another language, or because this file is English.

Code, paths, symbols, YAML keys, `Anchors`, `Related`, `[RETIRED]`, and the single description token `NOT` stay as written here.

When `language` is `zh`, descriptive sentences and these labels are Chinese:

- programmer description: the sentence in **One generation pass**. Still `len(compact) <= 280`. The trigger is still the module id.
- other skills: spoken when-to-use with `当用户`, plus one `NOT` or one `让位`. `len(compact) <= 240`.
- architect: `本仓库的架构约束与分层。当用户问改动属于哪一层，或是否违反架构。NOT 模块 API 写法 (programmer-*-skill)。`
- debug: `本仓库的边界与失败检查。当用户在查空引用、竞态或崩溃。NOT 模块 API 写法 (programmer-*-skill)。`
- profiler: `本仓库热路径性能复查。当用户说热路径慢、卡顿或在分配。NOT 功能错误 (debug-skill)。`
- programmer EXAMPLES labels: `功能`, `脚本`. Programmer MEMORY uses `规则` or `约定` for a rule, and `功能` / `脚本` only for a file locator. Other MEMORY labels: `规则`, `定义`, `检查清单`, `陷阱`, `现象`, `防护`.

English (`en`, the default) uses the formulas and labels in the sections below.

For any other code, write the body in that language. The description must still contain `Use when` or `当用户`, and exactly one `NOT`. `validate` only recognizes those tokens. Do not invent a third when-phrase.

## One generation pass

A queue card and a named `programmer-*-skill` (`castflow generate skills` included) use this same pass. Writing one skill, then clearing context, stops crosstalk. It is not a thinner skill. `coldstart --skill` does not write a skill body.

No eval loop. No description optimization. A programmer skill writes `SKILL.md` and `ITERATION_GUIDE.md`. Write `EXAMPLES.md` only when this pass located a feature in a script file. Nothing to locate means do not create that file. Do not write it empty. Do not invent a feature or a script path so the file exists. Write `SKILL_MEMORY.md` only when this pass found a rule to record. A rule includes an implicit rule and a convention, not only a heading that says Rule. Nothing to record means do not create that file. Do not write it empty. Do not invent a rule so the file exists. Do not omit `SKILL.md` or `ITERATION_GUIDE.md`. The scanner's display name is not a trigger: it is often a hot type. Acceptance of a programmer skill is `python .castflow-runtime/manager.py validate`. That command runs the programmer-skill check. Do not grade the skill yourself.

Two terms cover this pass. Do not invent a second name for either of them.

- **locator**: A locator is one feature plus the path of the one script file that holds it. The model reads that script for the API. A call site, a copied call shape, a line number, or a signature-gap body constraint is not required.
- **yield**: one neighbor the description steps aside for. The description text writes that yield as a single `NOT`.

Record a locator only when this pass found the feature in that script. Do not copy the call. Do not record what the function body requires. Ordinary edits inside a script that stays in place do not change the locator.

- English description: `Change <id> in this repo. Use when the user names <id>. NOT <one neighbor id>.` Do not write `Change <id> (<id>)`. Repeating the id in parentheses does not replace a display name. No neighbor you can name: `NOT work outside <id>.` That sentence includes the id, so it is not one shared yield.
- Chinese description: `改本仓库的 <id>。当用户点名 <id>。NOT <邻居 id>。` No neighbor: `NOT <id> 以外的工作。`
- A display name may replace the bare id only when it is not a generic type and is not the same string as the id: `Change <display> (<id>) in this repo. Use when the user names <display> or <id>. NOT <one neighbor id>.` Same caps, still one yield. Do not put Object, String, UI, Item, Config, or KeyValuePair in the description.
- Do not share one yield sentence across skills. Do not write `NOT other programmer-*-skill`. Do not write `NOT a different module` or `NOT 另一个模块`.
- Prose language is the card `language`, otherwise config. Missing means English.

For each feature you will locate:

1. Find the script that holds it. The card's `script_dirs` are search starts, not a closed file list.
2. Write one locator: the feature, then that script's repo-relative path. One feature, one file. Do not copy a call. Do not write a line number.
3. Write `SKILL_MEMORY.md` when the constraint is an implicit rule, a convention, or which file holds the feature and the examples do not already say that. If there is nothing to record, do not create `SKILL_MEMORY.md`. Do not invent a rule. Do not write a signature-gap body constraint.
4. `SKILL.md` states the duties this pass actually read, then points at a role file only when that file has a body. No protocol numbers, field dictionaries, or enum tables. Those are in the script the locator names. A table in the skill goes stale and overrides the repo. Do not add a duty you did not open. There is no quota of duties.

`EXAMPLES.md`: locators only. Fewer real features means fewer entries. Zero means do not create the file. Do not pad with a call, a declaration, or a file this pass did not open.

`SKILL_MEMORY.md`: implicit rules, conventions, and a file-level locator only when the examples do not already state it. Not a quota. No code fences. No dates. Nothing to record means do not create the file.

`ITERATION_GUIDE.md`: how to update **this skill**, not how to edit the module. Loaded at T4-MAINTAIN next to this file. This file is the shape of every skill. The guide is which event makes a locator lie, which of its own role files then changes, and how you know that edit is right. A programmer skill writes it. Do not leave it empty. Update a locator when its script file is added, removed, renamed, or the feature moves to another file. Do not update a locator because the implementation inside an existing script changed. The yield neighbor changing is the other trigger this pass can already name. Do not invent a product feature as a trigger. Do not reprint the duty table. Do not paste `SKILL.md` duties back as positioning.

Do not copy another repository's type names, message ids, or tab enums. A problem category may transfer. A symbol that does not exist here may not.

---

## Standard shape

Four role slots, not a quota of content. A `programmer-*-skill` has `SKILL.md` and `ITERATION_GUIDE.md` on disk. `EXAMPLES.md` exists only when a feature was located. `SKILL_MEMORY.md` exists only when a real rule does. Do not invent a script path, a rule, a duty, or an edit trigger so a file looks finished. Any other catalog skill has `SKILL.md`, plus another role file only when that file has a real job. Do not create an empty file or a heading-only file for those. Do not create a second case file.

Any extra `.md`, including under `references/`, fails validate once the directory is a catalog skill. Cases stay in `EXAMPLES.md` or one short fence in `SKILL.md`. A case does not get its own file. Scripts, schemas, and data files are the only extensions. A later evolution append writes a `SKILL_MEMORY.md` entry only when a real constraint exists. The first Append creates the file when it is absent. Append does not invent a first rule to justify the file.

| File | Write | Do not write |
|------|--------|--------------|
| `SKILL.md` | Who, when, who it yields to, where to read next | A tutorial, the full rules, an iteration log |
| `EXAMPLES.md` | One feature, and the script file that holds it | An empty file, a copied call, a line number, a spec |
| `SKILL_MEMORY.md` | A rule this pass found: an implicit rule, a convention, or a file locator the examples do not already state | An empty file, a signature-gap body rule, dates, code fences |
| `ITERATION_GUIDE.md` | When maintaining this skill, which of its files changes | How to edit the module, a reprint of this table, a check log |

An attachment only if the path uses it, and only if it is not markdown: `scripts/` for a deterministic step, or a schema / config / json / lookup table this skill reads. Those are the only extensions. One present role file names the file when it says when to read it or when to run it. No pointer means the file is dead, and validate fails it. Do not add `references/*.md` or a README of cases.

Do not emit ANALYSIS, TEMP, TODO, or SUMMARY. Do not open another markdown file to dodge the cap.

---

## SKILL.md

Once the host matches, the **whole file is in context**. Keep it to one screen. A long essay means the duties were mixed.

**YAML**: `name` and `description` only. No `when-to-use`, no other key the host ignores. No frontmatter on the other three files.

`description` is the always-on recall sentence, not a manual. One sentence of what it does, then `Use when` plus the concrete intent, then **one** `NOT` aimed at the sibling it collides with most. Length is characters after whitespace collapse (the `compact` string in `description_shape_errors`). Over the cap is an error. A missed recall beats a false one.

Not in the description: synonyms, slang, steps, a sibling catalog, or "use this even if nobody named it."

- Name matches `programmer-*-skill`: the description sentence from **One generation pass**. No synonym list, no class or path list, no extra yield. `len(compact) <= 280`.
- Other skills: spoken when-to-use, one `NOT`. `len(compact) <= 240`.
- `architect-skill` / `debug-skill` / `profiler-skill` use these sentences (tune only the NOT target):
  - architect: `Project architecture constraints and layering. Use when the user asks which layer a change belongs in, or whether it violates architecture. NOT module API how-to (programmer-*-skill).`
  - debug: `Boundary and failure inspection for this repo. Use when diagnosing null, race, or crash failures. NOT module API how-to (programmer-*-skill).`
  - profiler: `Hot-path performance review for this repo. Use when a hot path is slow, hitching, or allocating. NOT functional bugs (debug-skill).`

No keyword piles. Pushy expansion is an error: `even if they` / `even if the user`, `whenever the user mentions`, `make sure to use this skill whenever`, `即使没` / `即使不` / `即使用户没`. The body may name more yields. `NOT` appears at most once in the description.

Body order: one positioning sentence, Yield, as many duties as this pass read, then a link to each role file that has a body. Do not link an empty file. An attachment gets one line for when to read or run it. A module skill may name its real types and neighbors. That is still not a tutorial. Do not invent duties to reach a count.

One fence for a short formula. The feature's script path goes in EXAMPLES. Do not paste a call there as the API.

---

## EXAMPLES.md

One feature located in one script file. Fewer real features beat a padded file. No feature located means do not create this file. An empty file is not an entry. Over the cap: delete or merge **in this file**. The model opens that script and reads the API there.

```markdown
## Example N: short title

Feature
[what this feature is]

Script
[repo-relative path of one source file]
```

A call site, a copied call shape, and a line number are not required. Validate checks that the path exists and is a script. It does not read the calls or the function bodies in that file.

---

## SKILL_MEMORY.md

Hard rules, implicit rules, and conventions. As many as this pass actually found. Do not pad. Do not invent one. A programmer skill does not create this file until one real entry exists. A real entry is an implicit rule, a convention the module already follows, or a file locator the examples do not already state. A signature-gap body constraint is not an entry. A rule you cannot point at in the repo is not. The queue does not get a weaker bar. origin-evolve reads and writes this file. The first Append of a real constraint creates `SKILL_MEMORY.md` when it is absent. An empty file is not that append. No code fences.

Programmer rule or convention:

```markdown
### Rule N: name

[the implicit rule or the convention this pass found]
```

Programmer locator, only when examples do not already name the file:

```markdown
### Rule N: name

Feature
[which feature]

Script
[repo-relative path of one source file]
```

Other catalog skills use the symbol form below. A programmer rule may use it when a symbol can be grepped. A programmer locator does not: it stays the two labels above.

```markdown
### Rule N: name

Anchors: [class:Building/BuildingManager, method:Building/BuildingFunc:OnUpgrade]
Related: Rule X, Pitfall Y

Definition
[forbidden or required]

Check list
- [ ] checkable on the spot
```

```markdown
### Pitfall N: name

Anchors: [pattern:EventArgs.Create]
Related: Rule X

Symptom
[what it looks like]

Guard
[how to avoid it]
```

One constraint per entry. A check list only when the rule is verified step by step.

**Anchors** pin code symbols. Extended form `[kind:path-hint:symbol]`. Kind is `class`, `method`, `field`, `api`, or `pattern` (no prefix means `class`). Old form `[BuildingManager, OnUpgrade]` still counts. New writes use the extended form. An origin-evolve write carries both `Anchors:` and `Related:`. T4 may omit Anchors only when nothing greppable exists. An entry bound to code, or one evolve should Merge later, needs extended Anchors and Related. Empty Anchors have Jaccard 0, so evolve Appends a duplicate.

**Related** names the rules and pitfalls reviewed with this entry on Merge or Retire.

**[RETIRED]** prefixes the heading. Do not delete the body. Loaders skip it. Remove the mark to restore it.

```markdown
### [RETIRED] Rule N: name
```

Capacity writes need the user to confirm:

| Operation | T4 by hand | origin-evolve write |
|-----------|------------|---------------------|
| Append | No semantic overlap with an existing entry | No existing entry at Jaccard >= 0.5 |
| Merge | Same meaning or the same code region; show the diff | Jaccard >= 0.5 via `python .castflow-runtime/manager.py homology`. Do not invent another threshold here |
| Retire | Grep shows the Anchors symbols are gone | Same as Merge |

Near the cap, Merge or Retire before Append. Do not open a second rules file. Size is only the `validate` unit below. origin-evolve's word cap lives in that skill. Do not convert it into a second number here.

---

## ITERATION_GUIDE.md

This is the iteration manual for **this skill**. T4-MAINTAIN loads it with this file. `SKILL_ITERATION.md` says how every skill is shaped. The guide says when this skill has gone stale and which of its own files to edit. It is not read while writing product code. It does not say how to edit the module.

A programmer skill writes it. Empty is wrong for this file: the skill already has locators, a yield, or the fact that this pass found neither. Update a locator when its script file is added, removed, renamed, or the feature moves to another file. Do not update a locator because the implementation inside an existing script changed. Do not leave the file empty, and do not invent a product feature ("when a new building type ships") that this pass did not see.

Each rule: a trigger, the role file to edit, a check you can do on the spot. Enough rules for the facts this pass has. No quota.

Do not reprint this file's which-file table. Do not paste `SKILL.md` duties back as positioning. Do not write a quality metric you cannot check. An acceptance bar does not require a quality metric here.

Any other catalog skill does not create this file when its only text would be the file names.

---

## Format

- No emoji. No decorative Unicode (blocks, stars, check marks, crosses, Unicode arrows). ASCII `->`, Markdown, `- [ ]`, and `[RETIRED]` are fine.
- `SKILL_MEMORY.md` and `ITERATION_GUIDE.md`: no dates, no `Updated`, no `V2.0`, no sign-off line.
- A cited script path was Read this pass. Do not write a path you did not open. Do not write a signature. The model reads the script for that.

---

## Size

SKILL.md stays loaded. The rest open on demand. Do not pad. Do not split files to dodge the check.

Unit matches `_count_size_units` in `validate.py`: non-whitespace characters outside code fences. Over the cap warns.

| File | Enough | Warning cap |
|------|--------|-------------|
| SKILL.md | One screen | 4000 |
| EXAMPLES.md | One feature per entry; the path is short | 14000 |
| SKILL_MEMORY.md | One constraint per entry | 9000 |
| ITERATION_GUIDE.md | This skill's triggers only | 4500 |

SKILL.md points at a role file only when that file has a body, plus one line if an attachment exists. Add a contents table to EXAMPLES, MEMORY, or GUIDE only when the file needs jumps. A short file does not get an empty table. Do not create an empty `EXAMPLES.md` or `SKILL_MEMORY.md` so a table has a row.

---

## Which file

| Situation | SKILL.md | EXAMPLES.md | SKILL_MEMORY.md | ITERATION_GUIDE.md |
|-----------|----------|-------------|-----------------|-------------------|
| Script file added, removed, or renamed | | yes | maybe | yes |
| Feature moves to another file | | yes | maybe | yes |
| Implementation inside an existing script changed | | | | |
| Yield neighbor changed | yes | | | yes |

A blank cell means do not edit that file for that situation. The implementation row is blank on purpose: code inside a script that stays put is not a skill edit. On a programmer skill, `EXAMPLES.md` is not created when this pass found nothing to locate. `SKILL_MEMORY.md` is not created when this pass found no rule. `ITERATION_GUIDE.md` is written.

Then `python .castflow-runtime/manager.py validate`, then `python .castflow-runtime/manager.py sync`.
