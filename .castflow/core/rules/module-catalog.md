# Module catalog contract

Not a skill. Load only when scanning modules or generating module skills.
Do not auto-inject into ordinary coding turns.

There is no Python module scanner. Module discovery is the AI executing
`MODULE_SKILL_LOOP_ENGINE_SYSTEM_PROMPT.md` in the current session.

When the user pastes a scan-and-generate prompt (cold-start checkbox), the
model:

1. Walks **product** scripts (any language) and groups **logical functional**
   modules. Skip the AI framework entirely (see below).
2. Shows a host **multi-select** so the user picks which modules get a skill;
   each option must have a clickable/focus preview: description + script dirs
3. Writes one short card per selected module under
   `.castflow-runtime/_skill-gen-queue/`, then compacts unused scan context
4. Generates selected modules **one at a time** (read card -> write skill ->
   mark `status: done` -> compact). Deletes the queue directory when finished.
   Never generate two skills in parallel.

Do not split by assembly, `.asmdef`, or first-level folders. Do not stop
because there is no `Assets/Scripts` or `.cs`. Do not call `scan.py`,
`manager.py scan`, or any HTTP scan API.

When the user did not ask to scan or generate, do not walk the tree and do
not write skills.

## What counts as a module

A module is a top-level functional unit with its own types and a stable
script path.

- Prefer 3-8 accepted modules.
- One module may own several `script_dirs` / `paths` (same id merged).
- Split only when two public APIs or lifecycles barely import each other.
- Merge when one side is helpers, or either side has fewer than 3 script files.

Not a module by default (still show in the multi-select, unchecked):

- `util` / `utils` / `common` / `shared` / `test` / `tests` / `editor`
- every nested folder, generated code, vendor trees
- fragments with no stable public surface

Never a module (do not walk, do not list, do not generate `programmer-*-skill`):

- `CastFlow/` (framework repo: submodule, nested copy, or mistaken project root)
- `.castflow/` (CastFlow checkout harness; should not appear in a seeded project)
- `.castflow-runtime/` (the project's only CastFlow tree: skills, hooks, manager.
  Skip the whole tree. Do not list skill names. Anything already there is not a product module.)
- `.claude/` `.agents/` `.cursor/` `.grok/` (adapter discovery / projection)
- root `castflow.bat` / `castflow.sh` / `castflow.command`

The scan target is the user's product/game/app scripts. CastFlow is the
installer, not a product module. Path segments matching the names above
(case-insensitive for `CastFlow`) take the whole subtree out of scope.
Do not keep a roster of framework skill names to skip.

## Module card (AI fills; do not fabricate)

Required on each candidate before the multi-select:

- `id`, `name`, `responsibility`
- `script_dirs`, `scope_paths`, `core_symbols`
- `suggested_skill`, `recommend`, `recommend_reason`

`responsibility` is observed from scripts (and a directory README only if one
exists next to those scripts). Empty is better than an invented story.

Do not persist scan ledgers (`INVENTORY.md`, `STATE.yaml`, `catalog.json`
rows filled by a script). The multi-select **is** the review UI.
After the user submits the multi-select, persist **only selected** cards as
`.castflow-runtime/_skill-gen-queue/{NN}-{id}.yaml` (`status: pending`).
Do not write unselected modules. Delete the directory when every selected
skill is written.

## Two modes

**User asked to scan** (pasted generate prompt):

- AI scan -> multi-select with previews -> land selected cards -> compact
  -> generate one skill at a time from the queue -> delete the queue
- Any language
- After selection, recon stays inside that module's script paths
- Parallel generate subagents are forbidden (quality drops)

**User did not ask** (install-only cold start):

- Do not walk the tree
- Do not write skills

Forbidden in both modes:

- Writing skill sources into `.claude/skills` or `.agents/skills`
- Treating missing `.cs` / `Scripts` as "no modules"
- Generating before the user submits the multi-select
- Offering CastFlow / harness / adapter trees as skill-generation options
