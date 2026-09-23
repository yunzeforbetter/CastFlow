# Changelog

**English** | [中文](./CHANGELOG.zh-CN.md)

User-visible changes to CastFlow. Versions follow semver: a breaking workflow change is a major version, a new capability is a minor version, and a fix or a tightening of scope is a patch.

---

## 2.1.0 — 2026-09-18

**macOS cold start matches Windows.** The framework repo and an already installed project can both open the wizard / console on a Mac. You no longer have to detour through `python … launch` only.

### Added

- **`castflow.sh` / `castflow.command`**: POSIX launchers. Run `./castflow.sh` in a terminal; double-click `castflow.command` in Finder. They add Homebrew / python.org / pyenv to PATH (Finder starts with a very short PATH).
- **seed writes three launchers**: the project root gets `castflow.bat`, `castflow.sh`, and `castflow.command` together, so the same repo opens on Windows and Mac. `unseed` removes all three.
- **macOS folder picker**: `pick_dir.py` prefers the `osascript` system dialog. It does not depend on tkinter / `python-tk`.
- **`.gitattributes`**: `.sh` / `.command` are forced to LF, so a Windows checkout does not turn the shebang into `bash\r`.

### Changed

- Docs and the loop-engine exclusion list treat the Mac launchers the same as `castflow.bat`.

---

## 2.0.0 — 2026-09-18

**CastFlow 2.0: from "install by chat + a 9-step pipeline + score the editor" to "a GUI operating system + one skill source of truth + a memory ledger".**

**Why the rewrite: the models themselves are stronger now, and more sensitive.** 1.x used overly dense rules, orchestration, and scores to manage earlier models. Today those constraints burn context and turn "advice" into ritual, which limits judgment. 2.0 does not stack features on 1.x. It subtracts for what current models can do: drop subsystems that are expensive, easy to recall by mistake, or have no load path, and keep only the hard guardrails that are specific to the project.

The daily path is four steps: the wizard copies files → optionally let the AI generate module skills by logical feature → write code through the module skill → write a memory when you are corrected, and it becomes a rule after approval.

### 1.x compared with 2.0

| | 1.x | 2.0 |
|--|-----|-----|
| How you install | Tell the AI `bootstrap castflow`, answer language/modules, the model runs the commands | Double-click `castflow.bat` or run `manager.py launch`; CastFlow may live outside the project |
| Where knowledge is written | One copy per host: `.claude/skills`, `.grok/skills`, `.cursor/skills`, … | `.castflow-runtime/skills/` is the source; project only onto the Claude and Codex discovery paths |
| Where modules come from | `manager.py scan` splits by directory and file count | No Python scanner. The AI coarse-scans by logical feature; the host multi-selects; framework trees are hard-excluded |
| How many are generated at once | Up to 3 parallel sub-agents per batch | **One at a time**: queue, clear context, validate/sync, mark done |
| How a cross-module feature is done | `code-pipeline-skill` Step 1–9 + three dedicated agents | Call each `programmer-*-skill` directly. The pipeline is retired; sync clears leftovers |
| How experience enters the repo | Five-axis scores (F/D/K/S/E) watch the edit buffer; a pure code edit also produces a trace | Only snapshot the memory you wrote. No memory written = this session records nothing |
| How similar rules merge | The model invents Jaccard inside the skill body | `manager.py homology` computes connected components in one batch; thresholds are not written into the evolve skill |
| What the AI reads before writing code | A constraint checklist, Grep at least twice, named execution modes | Three protocols: prove before use, constraints override copied code, ask first when scope is not enough |
| Installed into the wrong place | Delete `.claude/` by hand | GUI rollback / `unseed`; project source is untouched |
| Evolution you do not want | The docs said it could be turned off, across scattered paths | Wizard or `evolve on\|off`: uninstall hooks and origin-evolve; traces stay |

### What actually got better

1. **Cold start no longer spends a conversation.** Language, adapters, evolution, and whether to scan are all done in the GUI. The agent does one thing: ask you to open the wizard; if the scan is checked, it then runs the `/goal` you pasted. Install is decoupled from content production. A failure can `unseed`.
2. **One source of truth, so hosts stop recalling the same skill twice.** Grok/Cursor used to copy a whole skill tree, and the same skill was scanned twice. Now only `.claude/skills` and `.agents/skills` are linked; compatibility leftovers are cleared by sync. Projection directories are ignored in full by an owned `.gitignore`, so a Windows junction is no longer committed by mistake and switching branches no longer breaks it.
3. **Modules follow the product, not the folders.** `scan.py` is gone, and so is "refuse unless there is `.cs` / `Assets/Scripts`". In the current session the AI groups by public types and lifecycle; you check the multi-select. `util` / `test` / `editor` are unchecked by default but still visible. CastFlow itself is never a module.
4. **Generation quality over throughput.** Parallel sub-agents stuffed scan fragments and three SKILL bodies into context at once. 2.0 forces: selected short cards are written to disk → unselected cards are dropped → read one card and write one skill → mark done only after validate passes. architect / debug / profiler are also one at a time.
5. **Evolution feedstock is "something you actually said".** Five-axis scores treated "how many lines changed" as "what was learned". The noise was high, and calibration burned another round. schema:4 embeds only the full memory text. A single `feedback` entry can qualify; other types need a homology cluster ≥ 2. A pure code session writes zero entries.
6. **Merge is a deterministic algorithm, not prose.** `_homology.py` uses slug / same skill / Anchors Jaccard≥0.5 as a union-find. Evolve must not invent its own threshold and must not spawn a Python process once per pair.
7. **Protocols are tightened to what current models can do, instead of binding a stronger model with overly dense rules.** A sensitive model treats checklists, Grep quotas, and named execution modes as rituals it cannot skip. `GLOBAL_SKILL_MEMORY` keeps only the three protocols. An unverified API is marked TODO on that call site; it no longer stops the whole patch. `SKILL_ITERATION` drops the scare section, bash scripts that cannot be run, and word counts that fight `validate.py`. A missed recall is better than a false one.
8. **The framework is a plugin, not a lock-in.** Evolution can be turned off. CastFlow can sit on another drive. The factory repo refuses to treat itself as the target project. `update-framework` refreshes the core and does not touch project skills.
9. **Long tasks have their own packager.** `goal-loop-creator` turns an evolving requirement into a resumable Goal Loop package (`RUN_PROMPT.md` + its own run state). It does not call `/goal` itself, and it does not compete with module scanning for the path.

### Added

- **Manager and GUI**: `.castflow/manager.py` + `manager/`. `launch` / `setup` / `unseed` / `update-framework` / `seed` / `sync` / `skills` / `retire` / `activate` / `update` / `evolve` / `queue` / `handoff` / `flush` / `homology` / `validate` / `status` / `ui`. A stdlib HTTP console: a four-step wizard before install, and Framework / Skills / Queue after install.
- **`castflow.bat`**: ASCII only (so cmd.exe code pages do not split Chinese into a broken command); folder picker; CastFlow does not have to live inside the project; cross-drive hooks are written with absolute paths.
- **`.castflow-runtime/`**: the only CastFlow directory in the target project. Source of truth for skills / memory / traces / protocols / config, plus hooks, the manager, and `module-catalog.md`. A vendored `.castflow/` is no longer copied in. `skills-state.json` remembers retirements; later syncs obey it and do not resurrect them.
- **Module-skill loop-engine**: `MODULE_MARK_SYSTEM_PROMPT.md` + `rules/module-catalog.md`. After the scan is checked, the default one-line prompt is `/goal 读取并按照 …MODULE_MARK_SYSTEM_PROMPT.md 执行`.
- **`unseed`**: removes the runtime and the projections (including the manager inside the project). Does not delete project source. `CastFlow/.castflow/` in the framework repo is left alone.
- **homology**: `core/hooks/_homology.py` and `manager.py homology` (stdin JSON → connected components).
- **`goal-loop-creator` promoted to a core skill (long-task compiler)**: seeded automatically at cold start and labeled on the wizard / Skills page. Compiles a requirement into a loop-engine long-task package the AI can run (Goal Loop Package, INTAKE→HANDOFF). Output lives in `loop-engine/packages/`, does not enter the skill source of truth, and does not execute `/goal`.
- **Projection gitignore**: sync writes a stable block at the project root that ignores `.claude/skills/`, `.agents/skills/`, `.grok/skills/`, and `.cursor/skills/` in full. Tracked paths are `git rm --cached`.
- **Factory-repo protection**: seed/sync/setup against the CastFlow repository itself are refused, and a runtime / adapter tree / root `CLAUDE.md` left there by mistake is deleted.
- **description shape check**: `validate.py` limits length (programmer 280 / others 240), allows `NOT` at most once, rejects extra YAML keys such as `when-to-use`, and rejects pushy expansions.

### Changed

- **The cold-start path** is the GUI (copy files). `bootstrap-skill` is deleted; the next sync / manager open clears leftovers in an already installed project.
- **Skill discovery** projects only Claude + Codex. Grok/Cursor scan those two paths; sync clears CastFlow copies under `.grok/skills` / `.cursor/skills`. Hook JSON and evolve-reminder are still written according to the adapter switches.
- **Module discovery** is an in-session AI flow (coarse scan → multi-select must stop → write cards → one at a time). The GUI no longer lists script-scan results.
- **Daily work** calls the module skill directly. Generation writes into the runtime and must not write the adapter mirror.
- **Evolution capture** is a schema:4 memory snapshot. The primary path is `.castflow-runtime/memory/`. Claude `~/.claude/projects/<slug>/memory/` is optional inbound only. `user` entries are filtered.
- **origin-evolve**: a block qualifies on `feedback+ok` or homology ≥ 2; `validated` does not authorize; homology runs as one batch; business rules are not written to `.claude/rules/`.
- **GLOBAL_SKILL_MEMORY**: only the three protocols remain. The same-file exemption applies only to the same symbol already written, with the same signature. A Grep hit is not evidence. When this conflicts with the root rules, the root rules win. Wait for confirmation only when the action is irreversible.
- **SKILL_ITERATION**: the four roles are still the standard. A non-markdown attachment is allowed when the chain needs it (and it must have a pointer). Size warnings go through `manager.py validate`. EXAMPLES copy the hot path from the repo; a "complete using list" is not required.
- **compaction**: age only. An experience asset (a snapshot, or `validated:true`) is never deleted automatically.
- **Root rules** are injected into `CLAUDE.md` / `AGENTS.md` only from `ROOT_RULES.template.md`.
- **Console**: before install, only the wizard is shown; after install, three pages. On the Framework page, "update from the CastFlow source and sync" is `update-framework`.
- **Test layout**: hook tests live in `test/hooks/`; added `test/manager/`, `test/hooks/test_homology.py`, and `test/skills/`; the entry point is `test/run_all.py`.
- **The target project keeps only `.castflow-runtime/`**: cold start writes the manager, hooks, `module-catalog.md`, and the ROOT_RULES template into the runtime. It no longer vendors `.castflow/`. Project commands are `python .castflow-runtime/manager.py`.
- **Disabling a skill is a local list**: `.castflow-runtime/skills-disabled.json` (gitignored). Anything not listed stays active. Opening the manager refreshes the projection.

### Removed

- `.castflow/core/skills/code-pipeline-skill/` and the `requirement-analysis` / `integration-matching` / `pipeline-verify` agents. sync clears leftovers in an installed project. trace-flush no longer consumes a pipeline result; a leftover `pending-pipeline` is marked invalid.
- `.castflow/manager/scan.py`, `manager.py scan`, `/api/scan`, `/api/preview-scan`.
- Five-axis scoring, the edit buffer, IDP, `traces/weights.json`, and score self-calibration (former evolve Step 6).
- `.castflow/core/templates/skills/programmer.template/`, `templates/agents/programmer.template.md`, `--templates-only`, `--agent`. The installer no longer ships `.claude/templates/`.
- `.castflow/core/templates/AUTHORING_GUIDE.md` (it duplicated SKILL_ITERATION; the Rubric was never executed by code).
- `.castflow/core/skills/skill-forge/`. Creation goes through skill-creator; the eval loop is forbidden during cold start.
- `.castflow/core/CLAUDE.template.md`, `.castflow/installer/placeholders.py`.
- bootstrap CLI: `--skill`, `--strict-content`, Phase B.
- `.castflow/bootstrap.py` and the installer's 1.x Phase A entry points (`cli.py` / `generate.py` / `backup.py` / `manifest.py` / `hook_config.py` / `claude_merge.py` / `templates.py` / `io_ops.py` / `paths.py`). Validation is only `installer/validate.py`, called by `manager.py validate`.
- Writing CastFlow skills into `.grok/skills` / `.cursor/skills`.
- `.castflow/bootstrap-assets/skill-templates/` (architect/debug/profiler domain templates). Recall sentences are inlined into `SKILL_ITERATION.md`.
- Top-level `bootstrap-skill/`. Cold start goes only through `castflow.bat` / `manager.py launch`.

### Fixed

- Projections committed to Git, and a Windows junction stored as a normal directory, broke on branch switch: ignore the whole directory + `git rm --cached`.
- UTF-8 Chinese in `castflow.bat` was split into illegal commands under cmd.exe, and CastFlow itself was mistaken for the project root.
- A checked scan treated `CastFlow/`, `.castflow/`, the runtime, and adapter trees as business modules.
- Module-skill descriptions were written as the pushy expansions skill-creator used to invent ("use this even if it was not named").
- bootstrap / manager docs still listed the deleted `scan` as a current command.
- Template UTF-8 BOM, and `open()` with no `encoding=` under Windows' default encoding (read and write Chinese across platforms).

### Upgrade notes (1.x → 2.0)

1. After `git pull`, run `python .castflow-runtime/manager.py update-framework` in the target project (or use the Framework page in the GUI). The framework source stays in the CastFlow repo; the project has only `.castflow-runtime/`.
2. Project skill bodies should live in `.castflow-runtime/skills/`. If they exist only in an adapter tree, copy them into the runtime before sync.
3. Do not call `code_pipeline` / `manager.py scan` / `bootstrap.py` anymore.
4. Write corrections to `.castflow-runtime/memory/` (`type: feedback`). Do not expect a line-count of code edits to trigger evolution.
5. Old traces (schema 1–3) can stay. Evolve ignores retired fields, and compaction drops the skeletons on its own.
6. If projection paths such as `.claude/skills` were committed, the next sync removes them from the index. The worktree link stays.

---

## 1.x archive

Records that landed before 2.0 and are now absorbed or replaced by 2.0. Kept for comparison. No longer tagged Unreleased on their own.

### 1.x install and multi-tool support (absorbed by the 2.0 manager)

- The skill source of truth was designed as a runtime from the start, then projected onto four hosts. 2.0 narrows that to the Claude + Codex discovery trees.
- The visual console, the evolution switch, `retire` / `update` / `sync`, and HTTP `/api/skills*` arrived late in 1.x. 2.0 adds `activate` / `unseed` / `homology` / `validate` / the folder picker.
- Cold start used to be seed → **scan** → ui → generate. 2.0 deletes scan; a checked scan copies a `/goal` instead.
- The canonical manifest name is `bootstrap-output/cf_manifest.json` (so it is not confused with Unity `Packages/manifest.json`). The old `manifest.json` can still be read.
- `find_project_root` / `find_harness_dir` are decoupled: CastFlow may be a subdirectory; `--project-root`.
- Three-way merge of CLAUDE.md; BackupSession LRU; hook config is merged incrementally and idempotently.
- i18n: manifest `language`, default Chinese; templates were fixed Chinese, and the language of generated content was controlled by the prompt.
- Renamed CostFlow → CastFlow; `SKILL_RULE.md` → `SKILL_ITERATION.md`.

### 1.x evolution (the scoring model, retired in 2.0)

- Five-axis weighted scores F/D/K/S/E; K in three bands; E as edit density; buffer `path|lines|edits|flags`.
- Automatic correction detection (the R flag); `weights.json` self-calibration.
- The collector grew to 18 language suffixes; non-code resources are filtered.
- SKILL_MEMORY gained Anchors / Related; Append / Merge / Retire; capacity control.
- origin-evolve ownership decision tree; the pending-reminder threshold lines up with evolve-reminder.
- compaction L0–L3, validated protection, audit-line expiry, blank-line cleanup.
- `result_str` in `apply_pipeline_result()` was used before it was set (now history, retired with the pipeline).

Those capture and scoring paths are replaced in 2.0 by the memory-snapshot ledger. If the fields still appear in an old `trace.md`, they only age out. New writes do not produce them.

### 1.x pipeline (deleted in 2.0)

- `code-pipeline-skill` was a composite orchestrator: step dispatch cards, Handoff L0/L1, `pipeline_merge.py` fail-closed, and a `pending-pipeline` signal.
- The design motive was a contractual close-out when several waves ran in parallel. In practice it soaked the shared agent, competed with module skills for the entry point, and a day-to-day change to one system did not need 9 steps.
- 2.0 deletes that skill and the three agents. Day-to-day changes go through the module skill.

### 1.x tests

- `test/hooks/test_evolution.py`, `test_365day_simulation.py` (and the removed 100-day suite), `test/bootstrap/test_bootstrap.py`, `test/origin-evolve/verify_redesign.py`.
- Hook tests moved from `.castflow/core/hooks/` to `CastFlow/test/hooks/`. bootstrap no longer ships test files.
- 2.0 adds manager / homology / GLOBAL_SKILL_MEMORY contract tests on top of that, wired together by `test/run_all.py`.
