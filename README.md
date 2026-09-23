# CastFlow 2.0

**English** | [中文](./README.zh-CN.md)

> **An AI assistant that understands your project on day one, and gets sharper the more you use it.**

CastFlow is a portable, evolvable **operating system for AI-assisted development**, aimed at **Claude Code / Grok TUI / Codex CLI / Cursor**.

**Why 2.0: models are stronger now, and more sensitive.** 1.x used dense rules, a 9-step orchestration, checklists, and scoring rituals to "control" earlier models. Today those constraints burn context and flatten judgment, so they limit the model instead of helping it. 2.0 keeps a few hard guardrails and gives the rest of the room back to the model.

In the product: the entry point changes from "chat through Phase 0–6" to "double-click the wizard"; the knowledge source changes from "one copy per host" to "one runtime, projected onto discovery paths"; daily work changes from "a 9-step pipeline" to "call the module skill and write"; the evolution feedstock changes from "score the editor" to "the memory snapshots you were going to write anyway".

Install once. It keeps evolving. The 1.x comparison and the full change list are in [CHANGELOG.md](./CHANGELOG.md) ([中文](./CHANGELOG.zh-CN.md)).

---

## Contents

- [Why 2.0](#why-20)
- [What 2.0 changes vs 1.x](#what-20-changes-vs-1x)
- [What it solves](#what-it-solves)
- [Core design](#core-design)
- [Cold-start module scan](#cold-start-module-scan)
- [Jev classification](#jev-classification)
- [Layout](#layout)
- [End to end: install to evolution](#end-to-end-install-to-evolution)
- [File list](#file-list)
- [Progressive disclosure (T1–T4)](#progressive-disclosure-t1t4)
- [Self-evolution](#self-evolution)
- [Command reference](#command-reference)
- [Upgrade and rollback](#upgrade-and-rollback)
- [Test suite](#test-suite)

---

## Why 2.0

CastFlow 1.x was built when models hallucinated more, overreached more, and needed to be walked through each step. The reasonable response then was: **freeze the process, fill in the checks, and turn experience into a score.**

After models got stronger, the same response started working against them:

- More rules mean a noisier always-on context. A sensitive model treats "advice" as a ritual it cannot break: it reports before it judges, and checks in before it acts.
- A 9-step pipeline, parallel sub-agents, and domain-template boilerplate do orchestration the model already knows how to do, while crowding out the attention it should spend reading the project.
- A five-axis score treats "how many lines changed" as "what was learned". Models are already sensitive to feedback. What is actually valuable is a correction the user stated, not edit density.

2.0 subtracts. It keeps only constraints that are project-specific, machine-checkable, or that a human must approve. Discovering modules, writing patches, and organizing long tasks go back to the stronger model. The framework owns **the source of truth, the projection, the load points, and the evolution ledger**. It does not play a second operating system that micromanages every step.

---

## What 2.0 changes vs 1.x

| Area | 1.x | 2.0 |
|------|-----|-----|
| Cold start | Ask language in chat, run seed/scan for you, Phase 0–6 | GUI wizard: config, optional Jev, copy files; `coldstart` scans packages; `unseed` to start over |
| Knowledge source | A separate tree per adapter (`.claude/skills`, …) | One source: `.castflow-runtime/skills/`; project only onto `.claude/skills` and `.agents/skills` |
| Module discovery | Python splits by directory and file count | `coldstart` cuts one package-merge tree. Optional Jev classifies what the structure does not decide. Framework trees are excluded |
| Writing skills | Parallel sub-agents, context squeezed thin | One at a time: queue card → clear context → write → validate/sync → mark done |
| Daily code changes | `code-pipeline-skill`, 9 steps | Call `programmer-<module>-skill` directly |
| Evolution feedstock | Five-axis scores + edit buffer + IDP | schema:4 **memory snapshot ledger**; a pure code session writes no entry |
| Rule merge | The model invents its own Jaccard | `manager.py homology` connected components, computed in one batch |
| Runtime protocol | Checklists, Grep quotas, named execution modes | Three rules: prove an API before you use it, constraints override copied code, ask first when scope is not enough |
| Where the framework lives | Must be a subdirectory of the project | Folder picker; CastFlow can sit on another drive; hooks rewrite to absolute paths |

**Removed on purpose in 2.0** (not unfinished — the rules were too dense and would constrain a stronger model): `code-pipeline-skill` and its three pipeline agents, the old `scan.py` ledger (not `coldstart`), five-axis scoring, programmer domain templates, `AUTHORING_GUIDE`, `skill-forge`, `CLAUDE.template.md`, `placeholders.py`, and a second copy written to `.grok/skills` / `.cursor/skills`.

---

## What it solves

Four ways an AI assistant loses control on a large project:

| Problem | Symptom | What CastFlow does |
|---------|---------|--------------------|
| Architecture amnesia | Inconsistent style, broken layering | `architect-skill` extracts rules from real code; T1 force-loads the runtime protocol |
| API hallucination | Calls that do not exist, invented signatures | Protocol 1: EXAMPLES, a definition you opened, or a pointer from the user — any one is enough. Mark unverified call sites TODO. Do not guess a signature |
| Fragmented knowledge | Rules live in chat and PR comments | Four role files (SKILL / EXAMPLES / SKILL_MEMORY / ITERATION_GUIDE). The files are the knowledge |
| Experience that does not accumulate | The same mistake next time | Shared `.castflow-runtime/memory` + `traces/` across tools; `origin evolve` distills them into rules and writes the source **after a human approves**, then syncs |

Project knowledge becomes a repo asset that is **executable, checkable, and iterable**.

---

## Core design

### 1. Cold start copies files. Scan-and-generate is optional

```bash
CastFlow\castflow.bat                 # Windows: print help, then open the wizard (pick the project first)
./castflow.sh                         # macOS / Linux: same (Finder: double-click castflow.command)
python .castflow/manager.py launch    # same (any OS; run inside the CastFlow repo)
python .castflow/manager.py setup     # headless: config + seed + sync
python .castflow/manager.py unseed    # remove the runtime and projections, then run the wizard again
python .castflow-runtime/manager.py update-framework   # an already installed target project
```

CastFlow does **not** have to live inside the project. The wizard uses the system folder dialog to pick the project root. Across drives, hooks are written with absolute paths.

- If "scan modules and generate skills" is unchecked: only framework skills and core files are copied. **No AI prompt is required.**
- If it is checked: you can edit the prompt. Empty uses the built-in `/goal` that reads `.castflow-runtime/skills/MODULE_MARK_SYSTEM_PROMPT.md`.
- The package scan and Jev marks are `manager.py coldstart`, below. They do not scan `CastFlow/`, `.castflow/`, `.castflow-runtime/`, or adapter trees.
- Jev is a separate checkbox, off by default. Checked copies `.castflow/jev/` into the runtime. The key is not part of the copy.
- The factory repo (CastFlow itself) refuses `seed` / `sync` / `setup` and deletes a runtime left there by mistake.

Skill bodies have one source of truth: `.castflow-runtime/skills/`. `sync` projects them onto `.claude/skills` and `.agents/skills` with a symlink, junction, or copy. Grok and Cursor scan those two paths. They do **not** each get a `.grok/skills` or `.cursor/skills` tree (leftovers are removed so the same skill is not recalled twice). Skills disabled on this machine are not projected (`.castflow-runtime/skills-disabled.json`, gitignored; anything not listed stays active). Opening the manager refreshes the projection. `sync` owns a stable block in the project-root `.gitignore` that ignores each projection directory. Tracked projections are `git rm --cached`; the worktree is not deleted. Runtime skill bodies can still be committed.

### Cold-start module scan

`manager.py coldstart` walks the product scripts once and prints a selectable cut. With no `--select` it writes nothing.

```bash
python .castflow/manager.py coldstart --root PATH [--target N]
python .castflow/manager.py coldstart --root PATH --select ID --queue
python .castflow/manager.py coldstart --root PATH --select ID --skill
```

On an installed project the command is `python .castflow-runtime/manager.py coldstart --root PATH`.

- Only product scripts. `CastFlow/`, `.castflow/`, `.castflow-runtime/`, adapter trees, `Library`, `node_modules`, and similar trees are skipped.
- An atom is a package the repo already has: a feature directory, `tools/<Name>`, an asmdef, or a vendor folder. An edge is a type-name reference. A `using` line is not an edge.
- Those atoms merge bottom-up into one tree. `--target` (default 16) picks a layer of that same tree, not a second clustering. Targets above 8 keep `Modules/<Feature>` nodes.
- Roles are rules on that cut, not another clustering: `feature`, `engine`, `tool`, `adapter`, `bootstrap`.
- A recommended skill is a feature that has an entry, or one of up to two engine packages that are not a mixed grab-bag. Tools, adapters, bootstrap, mechanisms, and mixed bundles stay listed and unchecked.
- One selected node is one skill. Nested packages are evidence inside that node, not extra skills.
- This is not the deleted `scan.py`. It does not write `STATE.yaml`, `INVENTORY.md`, `GRAPH.md`, or a knowledge graph.
- Optional overrides live in `.castflow-runtime/module-roles.txt`, one line of `atom-id-or-path-prefix role`.

`--queue` writes only the selected cards to `.castflow-runtime/_skill-gen-queue/`. `--skill` needs exactly one `--select`, writes that `programmer-<id>-skill` from real call sites, then deletes the queue.

### Jev classification

Optional, and off by default. The wizard checkbox copies `.castflow/jev/` into `.castflow-runtime/jev/`. Leave it unchecked and the module is not installed.

The key is `TYPESAFE_API_KEY` in `.castflow-runtime/secrets.env`. That file is gitignored. It is the only secret store; later keys are more lines in the same file. The key is not stored in `config.json`.

`coldstart` marks each package atom. The mark is on the package in the graph, not on the merged skill node:

- A clear structure never calls Jev. The prior keeps a shared leaf (`common`, `shared`, `util`, `utils`) as a tool, attaches a leaf that matches a single feature, keeps adapters and feature packages, and splits an engine with fan-in at least 8, fan-out at most 3, and no entry.
- A card the prior cannot decide goes to TypeSafe Jev (`system_one`) only when the module is installed and the key is accepted. Stances are `feature`, `shared_method`, `independent_system`, `framework_mechanism`, and `other`. The mark copies the official choice. It does not invent a probability.
- With no module or no key, those cards are `review`, and the command prints that Jev is not configured. Marking stays on the structural prior.

A mark's action is `keep`, `attach`, `split`, or `review`.

### 2. Progressive disclosure: load by moment

Skills are not dumped into context every turn. They load by **T1-PREPARE / T2-EXECUTE / T3-FEEDBACK / T4-MAINTAIN**: read the full runtime protocol before writing code, and do not reread it while writing. The authority is the project-root `CLAUDE.md` / `AGENTS.md`, generated from `ROOT_RULES.template.md`.

### 3. Work through module skills

A cross-module request calls the generated `programmer-<id>-skill` directly. Name `architect-skill` / `debug-skill` / `profiler-skill` only when you need an architecture boundary, a diagnosis, or a hot path (the wizard no longer offers those three). `code-pipeline-skill` is retired.

Generation discipline: after you check the scan, short cards land in `.castflow-runtime/_skill-gen-queue/`. Write one programmer skill at a time. Mark it `done` only after validate/sync succeed, then clear context. Parallel generation squeezes the context. Increments use the same loop-engine, or tell the AI `castflow generate skills` (skill-creator writes one, then stops).

### 4. Self-evolution: capture with no extra step, human in the loop

The **only** capture path for experience is a **memory snapshot** (schema:4). On a rework, a correction, or a hard constraint, write `.castflow-runtime/memory/` (YAML `name` + `type: feedback|project|reference`). The hook snapshots the full text into `trace.md`. Scoring, the edit buffer, and IDP are all retired.

- `user` entries (personal profile) are filtered and do not enter git
- A pure code session produces no trace entry — the ledger records only "what was learned"
- Distillation waits for `origin evolve`: read `<!-- MEMORY -->`, cluster with homology, propose Append/Merge/Retire, and write the source **after approval**, then sync

The evolution plugin can be turned off in the wizard or with `manager.py evolve on|off` (uninstalls the hooks and the origin-evolve projection; existing traces stay).

---

## Layout

```
CastFlow/
├── README.md                              # English (repo default)
├── README.zh-CN.md                        # Chinese
├── CHANGELOG.md                           # English changelog (repo default)
├── CHANGELOG.zh-CN.md                     # Chinese changelog
├── LICENSE                                # MIT
├── castflow.bat                           # Windows cold start: folder picker + GUI
├── castflow.sh / castflow.command         # macOS / Linux cold start (.command = Finder double-click)
│
├── .castflow/                             # Framework source (dormant after install; updated by git pull)
│   ├── manager.py                         # Main entry: launch / setup / seed / sync / skills …
│   ├── manager/                           # Cold start, projection, queue, evolution switch, stdlib HTTP console
│   │   ├── cli.py / setup.py / coldstart.py / jevmark.py / envfile.py
│   │   ├── adapters.py / skills.py / catalog.py
│   │   ├── evolution.py / queue.py / config.py / paths.py / pick_dir.py
│   │   ├── bundle.py                      # seed: manager/installer → runtime, and write project launchers
│   │   └── ui/server.py + static/index.html
│   ├── jev/                               # optional; copied to the runtime only when the wizard box is on
│   ├── installer/                         # validate.py; copied into the runtime by seed
│   └── core/                              # Core synced into the runtime by seed
│       ├── skills/
│       │   ├── GLOBAL_SKILL_MEMORY.md     # T1 runtime: three protocols
│       │   ├── SKILL_ITERATION.md         # Four role-file standard; validate checks shape
│       │   ├── MODULE_MARK_SYSTEM_PROMPT.md
│       │   ├── origin-evolve-skill/       # Read traces → Append/Merge/Retire proposals
│       │   ├── skill-creator/             # Catalog four-file set (eval loop is not part of cold start)
│       │   └── goal-loop-creator/         # Core: long-task compiler. Requirement → loop-engine package
│       ├── protocols/validated-protocol.md
│       ├── rules/
│       │   ├── evolve-reminder.md(.mdc)   # Remind origin evolve when entries are pending
│       │   └── module-catalog.md          # What counts as a module; AI reviews the table, it does not scan the tree
│       ├── hooks/
│       │   ├── trace-collector.py         # Full-text snapshot when memory is written
│       │   ├── trace-flush.py             # Flush the ledger at session end + age compaction
│       │   ├── _homology.py               # Jaccard connected components (one batch)
│       │   └── _castflow_paths.py         # Hooks locate the runtime
│       ├── templates/root/ROOT_RULES.template.md
│       └── traces/                        # schema:4 contract + limits / hooks.config
│
└── test/                                  # Framework regression (not distributed)
    ├── run_all.py
    ├── manager/                           # seed/sync, wizard, coldstart, Jev marks
    ├── hooks/                             # Snapshot capture, homology, compaction, 365 days
    ├── bootstrap/                         # validate.py four-file shape (test_validate.py)
    ├── skills/                            # GLOBAL_SKILL_MEMORY contract
    └── origin-evolve/                     # Deterministic brute-force check of the spec
```

### A user project after install

```
project-root/
├── CLAUDE.md / AGENTS.md                  # Framework section (ROOT_RULES) + project section
├── castflow.bat / castflow.sh / .command  # Open the runtime manager (written by seed, not the factory copies)
├── .castflow-runtime/                     # The only CastFlow directory inside the project
│   ├── manager.py / manager/ / installer/ # Console, sync, validate (bundled from the framework)
│   ├── hooks/                             # trace-collector / trace-flush / _homology
│   ├── skills/                            # Source of truth: full skill set (committable)
│   ├── memory/                            # Cross-tool feedback / project / reference
│   ├── traces/                            # trace.md ledger + config
│   ├── protocols/ / rules/                # Includes module-catalog.md
│   ├── templates/ROOT_RULES.template.md   # Flat copy (source is core/templates/root/)
│   ├── config.json                        # Adapters, evolution switch, jev_enabled (no key)
│   ├── secrets.env                        # Gitignored. TYPESAFE_API_KEY and later keys. Not in config.json
│   ├── jev/                               # Only when Jev was checked at cold start
│   ├── module-roles.txt                   # Optional: atom-id-or-path-prefix role
│   ├── skills-disabled.json               # Local disable list (gitignored, not in the repo)
│   └── _skill-gen-queue/                  # Selected coldstart cards (deleted after --skill)
├── .claude/skills/                        # Discovery mirror (gitignored, do not edit by hand)
├── .agents/skills/                        # Codex discovery mirror (gitignored)
├── .claude/settings.json                  # Claude hooks (merged incrementally)
├── .cursor/hooks.json                     # Cursor hooks (no .cursor/skills tree)
├── .grok/hooks/castflow.json              # Grok hooks (no .grok/skills tree)
└── CastFlow/                              # Optional submodule; may also live outside the project (framework source, not the project source of truth)
```

---

## End to end: install to evolution

### Step 1 — Get the framework

```bash
git submodule add https://github.com/yunzeforbetter/CastFlow.git
```

Putting CastFlow next to `.claude` is the least fuss, but it is not required. Clone it anywhere, open the launcher, and point the folder dialog at the game or app project.

### Step 2 — Cold start (open the launcher)

```bash
CastFlow\castflow.bat                  # Windows: double-click
chmod +x castflow.sh castflow.command  # macOS / Linux: first time
./castflow.sh                          # terminal; Finder: double-click castflow.command
# or: python3 CastFlow/.castflow/manager.py launch
```

| Step | Action | Result |
|------|--------|--------|
| 1 Configure | Language, adapters, evolution, optional Jev | `config.json`. The Jev module is copied only if checked |
| 2 Optional | Check scan-and-generate; edit the prompt if you want | Empty uses the built-in `/goal` |
| 3 Start cold start | seed + sync | Framework skills and core files are projected |
| 4 Scan | `coldstart --root` | Package cut, plus Jev marks when the module is installed |
| 5 AI (only if checked) | Paste the prompt | Generate from that prompt, one skill at a time |

After install the console has three pages: **Framework** (update from source and sync) / **Skills** (retire / activate / update / sync) / **Queue**. A wrong check is "roll back and cold-start again". Do not delete files by hand.

For cold start, open the launcher (Windows: double-click `castflow.bat`; macOS: double-click `castflow.command` or run `./castflow.sh`). Do not ask the AI to run seed for you.

### Step 3 — Scan modules

```bash
python .castflow-runtime/manager.py coldstart --root .
python .castflow-runtime/manager.py coldstart --root . --select some-id --queue
python .castflow-runtime/manager.py coldstart --root . --select some-id --skill
```

The first command prints the cut and the Jev marks. It does not write files. `--queue` keeps only the ids you selected. `--skill` writes one programmer skill from real call sites and then deletes the queue.

If the wizard's scan box was checked, pasting its `/goal` is a separate path: the AI generates one programmer skill at a time. Do not generate in parallel. Rules for the skill files are in `SKILL_ITERATION.md`. Write into the runtime, then sync.

Day-to-day increment:

```
Generate a skill for the xx system
```

### Step 4 — Change a feature

```
Add a batch-upgrade feature to the xx system
```

The host loads the matching `programmer-*-skill` from its description. Multiple modules each go through their own skill.

### Step 5 — Evolve on its own

Over a week you get corrected a few times. Each time, write one `feedback` memory. The hook has already snapshotted it into `trace.md`. A later session's `evolve-reminder` says:

```
Pending entries detected (including feedback snapshots). Suggested: origin evolve
```

The user types `origin evolve`:

1. If snapshots are unflushed, run `manager.py flush` first, then take the lock
2. Keep only `pending`; `homology` clusters MEMORY sub-blocks into connected components
3. A block qualifies when it is `feedback` with quality=ok, **or** the homologous cluster has size ≥ 2
4. Propose Append / Merge / Retire (grep Anchors and confirm they still exist in code before writing)
5. Approve one by one (a rejection is recorded as `EVOLVE_REJECTION`)
6. Write `.castflow-runtime/skills/`, replace the original entry with one `<!-- PROCESSED … -->` line, then `sync`

The new rule is in effect next session. That class of mistake is not repeated.

### Step 6 — Upgrade the framework

```bash
cd CastFlow && git pull
python .castflow-runtime/manager.py update-framework
```

This refreshes framework skills and core files only. It does **not** overwrite project skills. The project section of `CLAUDE.md` is left intact.

---

## File list

### `.castflow/manager.py` — product entry

| Module | Role |
|--------|------|
| `cli.py` | launch / setup / unseed / seed / sync / skills / retire / activate / update / evolve / queue / handoff / flush / homology / validate / status / update-framework / coldstart / ui |
| `setup.py` | Wizard and headless cold start; folder picker; copies Jev only when checked; the factory repo refuses seed |
| `coldstart.py` | Package-atom scan: one merge tree, a target cut, role rules. Writes nothing unless `--select` |
| `jevmark.py` | Loads optional `jev.mark`. Prior first; official Jev only for unresolved cards |
| `envfile.py` | Read and write `.castflow-runtime/secrets.env`. Never `config.json` |
| `adapters.py` | runtime ↔ `.claude/skills` + `.agents/skills`; owned gitignore; clear compatibility leftovers |
| `skills.py` | Inventory, local disable (`skills-disabled.json`), refresh from source |
| `bundle.py` | seed copies `manager.py` / `manager/` / `installer/` into the runtime and writes project-root `castflow.bat` / `castflow.sh` / `castflow.command` |
| `catalog.py` / `queue.py` | Console queue status and the optional `/goal` handoff |
| `evolution.py` | Evolution switch: uninstall hooks and the origin-evolve projection |
| `ui/` | stdlib HTTP console (`127.0.0.1`) |
| `.castflow/jev/` | Optional classifier (`mark.py`, `install.py`). Copied to `.castflow-runtime/jev/` only when the wizard box is on |

### `.castflow/installer/` — copied into the runtime by seed (validate)

Only `validate.py` remains. `manager.py validate` calls it. 1.x `bootstrap.py` / Phase A / the manifest / `.claude/.backups` are gone.

| Module | Role |
|--------|------|
| `validate.py` | No emoji / no dates / no leftover `{{` `}}` / description shape / word-count warning |

### `.castflow/core/` — what seed copies into the runtime

| Path | Role |
|------|------|
| `GLOBAL_SKILL_MEMORY.md` | Three protocols. T1 reads the full text; T2 does not reread it |
| `SKILL_ITERATION.md` | Four roles + Anchors/Related + attachment pointers; machine checks go through `manager.py validate` |
| `MODULE_MARK_SYSTEM_PROMPT.md` | The `/goal` run after the scan is checked: scan → multi-select → generate one at a time |
| `origin-evolve-skill/` | Distill memory snapshots; never runs by itself |
| `skill-creator/` | Catalog four-file set; the eval loop is forbidden during cold start |
| `goal-loop-creator/` | **Core skill / long-task compiler.** Installed automatically at cold start. Compiles a requirement into a Goal Loop Package the AI can run (loop-engine: name the system once and finish it). Does not execute `/goal` |
| `hooks/trace-collector.py` | Primary path `.castflow-runtime/memory/*.md`; optional inbound Claude auto-memory |
| `hooks/trace-flush.py` | Write a trace only when a snapshot exists; `--selftest` |
| `hooks/_homology.py` | slug / skill / Anchors Jaccard≥0.5 → connected components |
| `templates/root/ROOT_RULES.template.md` | Injected into `CLAUDE.md` / `AGENTS.md`; seed copies it to runtime `templates/` |
| `traces/` | schema:4 contract, `limits.json`, `hooks.config.json` |
| `rules/module-catalog.md` | Module convention for the optional `/goal` path; seed copies it to `.castflow-runtime/rules/` |
| `hooks/` | seed copies them to `.castflow-runtime/hooks/`; hook JSON points there |

There is no domain-skill template. When generating architect/debug/profiler, the YAML recall sentence is in `SKILL_ITERATION.md`; the body still follows that file. Do not wrap a module skill in a deleted `*.template.md`.

---

## Progressive disclosure (T1–T4)

Named `T<index>-<verb>`. The authority is the project-root `CLAUDE.md`.

| Moment | Trigger | What the AI reads on its own |
|--------|---------|------------------------------|
| **T1-PREPARE** | Before writing code | Full `GLOBAL_SKILL_MEMORY.md` + the target `SKILL_MEMORY.md` + EXAMPLES as needed |
| **T2-EXECUTE** | While writing | Do not reread; use the already loaded protocol 3 to decide whether to gather information first |
| **T3-FEEDBACK** | User feedback | `protocols/validated-protocol.md` |
| **T4-MAINTAIN** | Create or change skill structure | `SKILL_ITERATION.md` + the target `ITERATION_GUIDE.md` |

Separating the four roles is a hard constraint: code samples live only in EXAMPLES, hard rules only in SKILL_MEMORY, navigation in SKILL, evolution rules in ITERATION_GUIDE. Script or data attachments are allowed, but they must not be used to split EXAMPLES apart.

`description` is the always-on recall sentence (about 200 characters): what it does + when to use it + **one** NOT. A miss is better than a false recall. No synonym lists, and no "use this even if it was not named".

---

## Self-evolution

### Capture (hooks, zero tokens)

```
The model writes .castflow-runtime/memory/*.md (first frontmatter block: name + type)
   │  PostToolUse: Write/Edit
   ▼
trace-collector: fence parse → legal type → quality ok/thin → .trace_memory_snapshots
   │  Stop (the whole step is a no-op if .trace_lock exists)
   ▼
trace-flush: write trace.md only when a snapshot exists (<!-- MEMORY --> sub-block) → age compaction
```

Code edits are no longer captured and no longer scored. A normal session should not read `trace.md` or `memory/`. The reminder looks only at `.unflushed` / `.evolve_nudge`. A host with no Stop hook (Codex) should run `manager.py flush`.

| Platform | Config | Capture | End |
|----------|--------|---------|-----|
| Claude Code | `.claude/settings.json` | `PostToolUse(Write/Edit/MultiEdit)` | `Stop` |
| Cursor | `.cursor/hooks.json` | `afterFileEdit` | `stop` |
| Grok | `.grok/hooks/castflow.json` | Same class of PostToolUse | `Stop` |

### Trace (schema:4)

```
<!-- TRACE status:pending schema:4 -->
timestamp: 2026-07-03T13:00:00Z
type: feedback
validated: _
memory_snapshots: 1
<!-- MEMORY slug:observablelist-ordered-insert type:feedback -->
description: ObservableList ordered insert must use Insert, not Add
---
(full memory text)
<!-- /MEMORY -->
<!-- /TRACE -->
```

Old schema:1–3 entries may still carry retired fields such as `score` / `modules` / `correction`. Evolve does not error on them and does not depend on them. Compaction drops them over time.

### Age compaction

An **experience asset** that has a memory snapshot or `validated:true` is never deleted automatically.

| Level | Trigger | Policy |
|-------|---------|--------|
| L0 | Every flush | Drop expired PROCESSED audit lines |
| L1 | — | Remove `validated:invalid` skeletons |
| L2 | entries/size over threshold | Remove over-age non-asset skeletons |
| L3 | Still over threshold after L2 | Overflow by age; always keep the latest `keep_recent_n` (default 20) |

Thresholds are in `traces/config/limits.json`.

### origin-evolve

Never runs by itself. A MEMORY block qualifies when it is `feedback`+ok, or its homology cluster size is ≥ 2. `validated` only sorts; it does not authorize.

```
Step 0 flush (if needed) → lock
Step 1 Triage (schema 1–4 / pending / one homology batch)
Step 2 Distill (grep to verify named APIs)
Step 3 Propose (ownership decision tree + Append/Merge/Retire + capacity)
Step 4 Approve one by one
Step 5 Write the runtime + PROCESSED line + sync; finally drop the lock
```

**Anchors**: `[kind:path-hint:symbol]`, `kind ∈ {class, method, field, api, pattern}`. The old form `[BuildingManager, OnUpgrade]` is still accepted.

Business rules are written only into a project skill or `.castflow-runtime/rules/cross-cutting.md`. Never into GLOBAL, `CLAUDE.md`, hooks, or origin-evolve itself.

---

## Command reference

### Phrases that trigger the AI

| Phrase | Action |
|--------|--------|
| Cold start | Open the launcher (`castflow.bat` / `castflow.sh` / `castflow.command`) |
| The pasted `/goal` scan prompt | Follow the loop-engine: programmer-*, one at a time |
| `castflow generate skills` | skill-creator: write one (a queue item / programmer / a named architect, debug, or profiler), then stop |
| Generate a loop / a `/goal` long task / turn a requirement into a long task | **goal-loop-creator**: compile a Goal Loop Package; do not execute `/goal` |
| `origin evolve` | Distill traces (when evolution is on) |

### manager.py (main entry)

Inside the CastFlow repo, use `.castflow/manager.py`. An installed target project has only `.castflow-runtime/`, so use the second form below.

```bash
CastFlow\castflow.bat                          # Windows
./castflow.sh                                  # macOS / Linux (or double-click castflow.command)
python .castflow/manager.py launch             # CastFlow repo: wizard
python .castflow-runtime/manager.py ui         # Target project: console
python .castflow/manager.py setup              # Headless seed+sync (inside the repo + --project-root)
python .castflow-runtime/manager.py unseed
python .castflow-runtime/manager.py update-framework
python .castflow-runtime/manager.py seed
python .castflow-runtime/manager.py skills
python .castflow-runtime/manager.py retire NAME
python .castflow-runtime/manager.py activate NAME
python .castflow-runtime/manager.py update NAME
python .castflow-runtime/manager.py sync
python .castflow-runtime/manager.py evolve on|off
python .castflow-runtime/manager.py queue
python .castflow-runtime/manager.py handoff
python .castflow-runtime/manager.py flush              # Flush by hand when there is no Stop hook
python .castflow-runtime/manager.py homology           # stdin JSON → connected components
python .castflow-runtime/manager.py validate
python .castflow-runtime/manager.py status
python .castflow-runtime/manager.py coldstart --root PATH [--target N]
python .castflow-runtime/manager.py coldstart --root PATH --select ID --queue
python .castflow-runtime/manager.py coldstart --root PATH --select ID --skill
python .castflow/core/hooks/trace-flush.py --selftest
```

If `python` does nothing: on Windows check PATH or use `py -3`; on macOS use `python3` (python.org or `brew install python`). When Finder double-clicks `.command`, the launcher adds Homebrew / python.org to PATH. The macOS folder picker uses the system dialog and does not depend on tkinter.

### Who owns which files

| Class | Owner | How it updates |
|-------|-------|----------------|
| `CastFlow/` | This repo | `git pull` / submodule update |
| `CLAUDE.md` framework section | seed / ROOT_RULES | Merged at install |
| `CLAUDE.md` project section | The project team | Edit directly |
| `.castflow-runtime/skills/` core | The framework | `update-framework` / `update NAME` |
| `.castflow-runtime/skills/` project | The team + evolve | loop-engine / skill-creator / approved writes |
| Adapter `*/skills/` | sync | Do not edit by hand |
| `.castflow-runtime/traces/` | Hooks + evolve | Do not edit by hand |
| `.castflow-runtime/memory/` | You, when correcting | Do not write `type: user` |

Do not edit `CastFlow/.castflow/` by hand (`git pull` overwrites it). Customization belongs in the runtime and in the project section of `CLAUDE.md`.

---

## Upgrade and rollback

```bash
cd CastFlow && git pull
python .castflow-runtime/manager.py update-framework
```

This refreshes framework skills and core files only (hooks, the root-rules template, `SKILL_ITERATION`, and so on). It does **not** overwrite project skills such as `programmer-*-skill`. The project section of `CLAUDE.md` is left intact.

`update-framework` does **not** write `.claude/.backups/` (the 1.x installer is gone).

Install-level rollback: the GUI action "roll back and cold-start again", or `python .castflow-runtime/manager.py unseed` (removes the runtime, the projections, and the project launchers; does not delete project source). Then open the launcher from the framework repo again.

---

## Test suite

Everything lives in `CastFlow/test/` (**not distributed**). No third-party dependencies (`unittest`). Each run is isolated in a temp directory.

```bash
cd CastFlow
py test/run_all.py
# or
py -m unittest discover -s test -p "test_*.py" -t .

py test/hooks/test_evolution.py
py test/hooks/test_homology.py
py test/hooks/test_365day_simulation.py --keep-data
py test/bootstrap/test_validate.py
py test/manager/test_setup.py
py test/origin-evolve/verify_redesign.py

# macOS / Linux: use python3 instead of py
```

`run_all.py` also runs `trace-flush.py --selftest`.

| Layer | Covered | Notes |
|-------|---------|-------|
| Python correctness | Yes | Capture gate, compaction, homology, validate, seed/sync |
| Data format and flow | Yes | Real `trace.md` write / read / compact |
| Hook event firing | No | Tests call functions directly; they do not simulate host stdin JSON |
| origin-evolve pattern recognition | No | AI behavior; the deterministic part is `verify_redesign.py` |
| User approval | No | Human in the loop |

Tests guarantee the **data pipeline is mechanically correct**: long-running writes do not corrupt the ledger, do not grow without bound, and do not drop experience assets. Generation quality is held by `SKILL_ITERATION` + `validate.py` + a human in the loop.

---

## LICENSE

See [LICENSE](./LICENSE) (MIT).
