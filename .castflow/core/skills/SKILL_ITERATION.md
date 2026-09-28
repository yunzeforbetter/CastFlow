---
name: skill-iteration
description: >
  CastFlow four-file skill format. Use only when creating or restructuring
  a skill, or when skill-creator asks for the format. NOT for implementing
  features.
---

# SKILL_ITERATION.md

Shape of a skill file. Load only at **T4-MAINTAIN** (create a skill, or change its structure). Calling a skill to write code is `GLOBAL_SKILL_MEMORY.md` and the project `CLAUDE.md`, not here.

Write the skill under `.castflow-runtime/skills/<name>/`. Do not write adapter mirrors. `python .castflow-runtime/manager.py sync` projects only `.claude/skills` and `.agents/skills`. Do not create `.grok/skills` or `.cursor/skills` (compatibility residue; sync deletes them so they are not scanned twice).

A `programmer-*-skill` follows this file only. No domain README, no `*.template.md`. Architect / debug / profiler recall sentences are below; their bodies still follow this file. If one role file contains both `{{` and `}}`, validate fails it as a leftover placeholder. The check is a raw substring, not a token shape. If copied sample code contains that pair, rewrite the sample.

An orchestration doc passes a skill name, a scope, and paths. It does not copy this file.

This file constrains **catalog and module skills**. Agents, this file, and freeform eval attachments have their own shapes.

Check: `python .castflow-runtime/manager.py validate`. A directory is a catalog skill when it has `SKILL.md` and every markdown file is one of `SKILL.md`, `EXAMPLES.md`, `SKILL_MEMORY.md`, `ITERATION_GUIDE.md`, or when a catalog skill also contains another markdown file. Missing optional role files are not errors and the directory is not skipped. A present role file that is empty or only headings is an **error**. Another markdown file on that catalog skill is an **error**. A non-markdown attachment with no pointer from a present role file is an **error**. Bad description shape, `{{` plus `}}` in one file, or emoji is an **error**. A directory whose markdown is outside that set (no `SKILL.md`, or only nested markdown such as skill-creator) is skipped, not failed. Over the size cap is a **warning**, not permission to open another file.

## Prose language

Generated skill prose uses the cold-start choice. Read `language` on the queue card, otherwise `.castflow-runtime/config.json` key `language`. Missing, empty, or `en` means English. `zh` means Chinese. Any other code means that language. Default is English. Do not switch because repo comments are in another language, or because this file is English.

Code, paths, symbols, YAML keys, `Anchors`, `Related`, `[RETIRED]`, and the single description token `NOT` stay as written here.

When `language` is `zh`, descriptive sentences and these labels are Chinese:

- programmer description: the sentence in **One generation pass**. Still `len(compact) <= 280`. The trigger is still the module id.
- other skills: spoken when-to-use with `当用户`, plus one `NOT` or one `让位`. `len(compact) <= 240`.
- architect: `本仓库的架构约束与分层。当用户问改动属于哪一层，或是否违反架构。NOT 模块 API 写法 (programmer-*-skill)。`
- debug: `本仓库的边界与失败检查。当用户在查空引用、竞态或崩溃。NOT 模块 API 写法 (programmer-*-skill)。`
- profiler: `本仓库热路径性能复查。当用户说热路径慢、卡顿或在分配。NOT 功能错误 (debug-skill)。`
- EXAMPLES labels: `场景`, `代码`, `项目参考`. MEMORY labels: `规则`, `定义`, `检查清单`, `陷阱`, `现象`, `防护`.

English (`en`, the default) uses the formulas and labels in the sections below.

For any other code, write the body in that language. The description must still contain `Use when` or `当用户`, and exactly one `NOT`. `validate` only recognizes those tokens. Do not invent a third when-phrase.

## One generation pass

A queue card and a named `programmer-*-skill` (`castflow generate skills` included) use this same pass. Writing one skill, then clearing context, stops crosstalk. It is not a thinner skill. `coldstart --skill` does not write a skill body.

No eval loop. No description optimization. Do not fill a role file to make four files. The scanner's display name is not a trigger: it is often a hot type. Acceptance of a programmer skill is `python .castflow-runtime/manager.py validate`. That command runs the programmer-skill check. Do not grade the skill yourself.

Three terms cover this pass. Do not invent a second name for any of them.

- **call site**: a reference other than the definition. A declaration, an empty body, or a Publish or Invoke with no subscriber is not a call site. Do not describe a call site as a registry. Cite each one as `path:line` under Project reference.
- **signature gap**: the definition body requires something the signature does not state, so a signature-only read would emit the wrong call. The memory entry names that body requirement, and its anchor greps in this repo.
- **yield**: one neighbor the description steps aside for. The description text writes that yield as a single `NOT`.

Keep a line only when omitting it would make the next generated call use the wrong symbol or the wrong argument. A fact the signature already states stays an example, not a rule.

- English description: `Change <id> in this repo. Use when the user names <id>. NOT <one neighbor id>.` Do not write `Change <id> (<id>)`. Repeating the id in parentheses does not replace a display name. No neighbor you can name: `NOT work outside <id>.` That sentence includes the id, so it is not one shared yield.
- Chinese description: `改本仓库的 <id>。当用户点名 <id>。NOT <邻居 id>。` No neighbor: `NOT <id> 以外的工作。`
- A display name may replace the bare id only when it is not a generic type and is not the same string as the id: `Change <display> (<id>) in this repo. Use when the user names <display> or <id>. NOT <one neighbor id>.` Same caps, still one yield. Do not put Object, String, UI, Item, Config, or KeyValuePair in the description.
- Do not share one yield sentence across skills. Do not write `NOT other programmer-*-skill`. Do not write `NOT a different module` or `NOT 另一个模块`.
- Prose language is the card `language`, otherwise config. Missing means English.

For each call site you will name:

1. Find it in product scripts. The card's `script_dirs` are where declarations live, not the boundary of callers.
2. Cite `path:line` of the call site, not the definition. Copy that call into `EXAMPLES.md`.
3. Open the definition body. If there is a signature gap, write one `SKILL_MEMORY.md` entry for it. If there is no signature gap, do not write `SKILL_MEMORY.md`.
4. `SKILL.md` points at the call site in one sentence. No protocol numbers, field dictionaries, or enum tables. Those are in files the model can open. A table in the skill goes stale and overrides the repo.

`EXAMPLES.md`: only when this pass opened a call site. About 3-8 call sites that change what is generated. Fewer real call sites means fewer examples. Zero means do not write the file. Do not pad with a declaration, an empty body, or a Publish or Invoke that has no subscriber.

`SKILL_MEMORY.md`: only a signature gap the keep test above keeps. Not a quota. No code fences. No dates.

`ITERATION_GUIDE.md`: only when this skill has its own acceptance bar. The file names are not that bar. An acceptance bar does not require this file.

Do not copy another repository's type names, message ids, or tab enums. A problem category may transfer. A symbol that does not exist here may not.

---

## Standard shape

Four role slots, not a quota. `SKILL.md` is the only file every catalog skill has. A one-sentence skill is `SKILL.md` alone: the recall sentence is the description, and the body does not need the other three files. Write another role file only when it has a real job. Do not create an empty file, a heading-only file, or a second case file.

Any extra `.md`, including under `references/`, fails validate once the directory is a catalog skill. Cases stay in `EXAMPLES.md` or one short fence in `SKILL.md`. A case does not get its own file. Scripts, schemas, and data files are the only extensions. A later evolution append creates `SKILL_MEMORY.md` only when a real constraint exists.

| File | Write | Do not write |
|------|--------|--------------|
| `SKILL.md` | Who, when, who it yields to, where to read next | A tutorial, the full rules, an iteration log |
| `EXAMPLES.md` | Hot paths copied on almost every call | A spec, the module catalog, a second case library |
| `SKILL_MEMORY.md` | Non-negotiable constraints and traps | Dates, versions, process notes, code fences |
| `ITERATION_GUIDE.md` | When **this** skill edits which file | A reprint of this table, a check log |

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

Body order: one positioning sentence, Yield, as many duties as exist, then a link to each role file that exists. Do not link a file you did not write. An attachment gets one line for when to read or run it. A module skill may name its real types and neighbors. That is still not a tutorial.

One fence for a short formula. Pasteable usage goes in EXAMPLES.

---

## EXAMPLES.md

Only call sites that change what is generated. About 3-8. Fewer real call sites beat a padded file. Over the cap: delete or merge **in this file**.

Each entry: one-sentence scene, code copied from the repo, a path or symbol that greps. Imports only need to make the call readable. Do not invent an API.

```markdown
## Example N: short title

Scene
[when to copy this]

Code
[fragment copied from the project]

Project reference
[real path or symbol]
```

A trap only if someone will actually hit it.

---

## SKILL_MEMORY.md

Hard rules and common traps. As many as exist. Do not pad, and do not create this file until one exists. A new entry must be a signature gap that the keep test in **One generation pass** keeps. The queue does not get a weaker bar. origin-evolve reads and writes this file. The first Append of a real constraint creates `SKILL_MEMORY.md` when it is absent. An empty file is not that append. No code fences.

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

Only this skill's triggers: which change edits which file, and how you know the edit is right. Do not create this file when those triggers are just the file names. Do not reprint this file. Do not paste SKILL.md duties back as "positioning." Quality measures only when this skill has its own acceptance bar.

---

## Format

- No emoji. No decorative Unicode (blocks, stars, check marks, crosses, Unicode arrows). ASCII `->`, Markdown, `- [ ]`, and `[RETIRED]` are fine.
- `SKILL_MEMORY.md` and `ITERATION_GUIDE.md`: no dates, no `Updated`, no `V2.0`, no sign-off line.
- A cited path, class, or method was Read or Grepped this pass. Do not write a signature you did not open.

---

## Size

SKILL.md stays loaded. The rest open on demand. Do not pad. Do not split files to dodge the check.

Unit matches `_count_size_units` in `validate.py`: non-whitespace characters outside code fences. Over the cap warns.

| File | Enough | Warning cap |
|------|--------|-------------|
| SKILL.md | One screen | 4000 |
| EXAMPLES.md | 3-8 call sites; code may be long | 14000 |
| SKILL_MEMORY.md | One constraint per entry | 9000 |
| ITERATION_GUIDE.md | This skill's triggers only | 4500 |

SKILL.md points at a role file only when that file exists, plus one line if an attachment exists. Add a contents table to EXAMPLES, MEMORY, or GUIDE only when the file needs jumps. A short file does not get an empty table. A missing role file does not get a stub so the table has a row.

---

## Which file

| Situation | SKILL.md | EXAMPLES.md | SKILL_MEMORY.md | ITERATION_GUIDE.md |
|-----------|----------|-------------|-----------------|-------------------|
| New call site | | yes | maybe | |
| New constraint or trap | | | yes | |
| Duty or trigger changed | yes | maybe | maybe | yes |
| Framework API changed | | yes | maybe | |
| User corrected a usage | | yes | maybe | |

Then `python .castflow-runtime/manager.py validate`, then `python .castflow-runtime/manager.py sync`.
