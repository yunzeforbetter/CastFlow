# Module catalog contract

Not a skill. Load only when scanning modules or generating module skills.
Do not auto-inject into ordinary coding turns.

Module discovery for a cold-start checkbox is one ephemeral command, then the
AI executes `MODULE_MARK_SYSTEM_PROMPT.md` for the multi-select
and the one-at-a-time skill write:

```text
python .castflow/manager.py coldstart --root <project>
```

(Use `.castflow-runtime/manager.py` after seed.) Optional `--target N`
selects a layer of one dependency tree (8 and 30 are coarser and finer cuts
of the same merges, not a new clustering). The command prints every module
at that cut. Each module nests one or more package atoms (paths, declared
types, how many other packages reference it). An atom is evidence for that
one skill, not a multi-select row and not a skill. It does not write a
ledger. Do not call deleted `scan.py`, `manager.py scan`, or any HTTP scan API.

When the user pastes a scan-and-generate prompt (cold-start checkbox), the
model:

1. Runs `coldstart` on **product** scripts, then applies
   `module-mark-skill` before the checkbox. Marks score four stances
   (feature, shared method, independent system, framework mechanism)
   and may attach, split, or keep a package. Accepted marks live in
   `.castflow-runtime/module-marks.txt` and win over a grab-bag path
   cut. `coldstart` uses official TypeSafe System One only when
   `TYPESAFE_API_KEY` is set; otherwise it prints that Jev is not
   configured and keeps the structural prior. The skill states no
   language and no directory names. Atoms are
   packages the repo
   already has: `GameLogic/**/Modules/<Feature>` (Logic and Runtime of the
   same feature are one atom), `tools/<Name>`, vendor trees, and an asmdef
   only when it is not a grab-bag around those features. Edges are distinct
   declared type names (C#: type-name references, not `using`, not raw token
   counts). Roles are tool / engine / feature / adapter / bootstrap. Skip
   the AI framework entirely (see below).
2. Shows a host **multi-select** of **every** printed module, in that
   order, not one row per atom. Each option is a label plus one sentence
   of meaning (role and how many packages reference it). Do not put atom
   rows, symbols, or directory trees in the question. `recommend: yes` is
   the default check (features with entries, plus the highest fan-in
   engines). Tools and adapters stay in the list unchecked. Do not hide
   them and do not turn the target knob into "only show 8 rows".
3. Writes one short card per selected module under
   `.castflow-runtime/_skill-gen-queue/`, then compacts unused scan context.
   Or pass `--select <id> --queue` for exactly the ids the user chose.
   The card keeps the one-line meaning and at most six script roots.
   Skill generation searches those roots again; it does not reuse a
   symbol list from the scan.
4. Generates selected modules **one at a time** (read card -> write skill ->
   mark `status: done` -> compact). `--select <id> --skill` writes one skill
   from real call sites and then deletes the queue. Never generate two skills
   in parallel.

Do not split a grab-bag asmdef or the first two path segments into the
checkbox. Do not cluster files or functions. Do not stop because there is
no `Assets/Scripts` or `.cs`. Do not hide rows to keep a short list. A
grab-bag assembly's leftover scripts stay one residue engine, not one
module per file.

When the user did not ask to scan or generate, do not walk the tree and do
not write skills.

## What counts as a module

A module is the user-selected skill unit: one node of the package tree.
It owns one or more atoms. List every module at the current cut. Do not
list every atom. 3-8 is not a cap on the printed list. `--target` only
chooses which layer of the same tree is printed.

- Order is role, then how many other packages reference the node, then id.
  `recommend: yes` rows come first.
- One module may own several atoms, `script_dirs`, and `paths`.
- The same `Modules/<Feature>` name under Logic and Runtime is one atom.
- A symbol or path from another module's atoms does not belong on this card.
- `util` / `test` / `editor` / protocol / vendor stay listed. Their
  `recommend` is no. They are not skills until the user checks them.
- One skill is one checked node. Nested atoms are not extra skills.
- Optional `.castflow-runtime/module-roles.txt` lines
  (`id-or-path-prefix role`) override a role before the cut. The scan
  reads that file and does not write it. It is not a graph ledger.

Not selected by default (still show in the multi-select, unchecked):

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

## Module card (written only after the user checks it)

Do not build this card before the multi-select. The printed module line is
enough to ask. After the check, the queue file is a search hint:

- `id`, `name`, `role`, `responsibility` (one sentence)
- `script_dirs`: at most six roots, nested folders folded up
- `atoms`: ids only
- `suggested_skill`

No `scope_paths`, `core_symbols`, per-file paths, or symbol lists. Generation
finds declarations under `script_dirs` and call sites across product scripts.
`responsibility` comes from the module line (role, id, reference count), not
from reading scripts during the checkbox. Empty is better than an invented story.

Do not persist scan ledgers (`INVENTORY.md`, `STATE.yaml`, `GRAPH.md`,
`PREFLIGHT.md`, `CLAIMS.yaml`, `knowledge-graph.json`, `.ua/`). The
multi-select **is** the review UI. `coldstart` without `--select` only prints.
After the user submits the multi-select, persist **only selected** cards as
`.castflow-runtime/_skill-gen-queue/{NN}-{id}.yaml` (`status: pending`).
Do not write unselected modules. Delete the directory when every selected
skill is written.

## Two modes

**User asked to scan** (pasted generate prompt):

- AI scan -> multi-select with previews -> land selected cards -> compact
  -> generate one skill at a time from the queue -> delete the queue
- Any language
- After selection, look for declarations under that card's script roots;
  call sites are still searched across product scripts
- Parallel generate subagents are forbidden (quality drops)

**User did not ask** (install-only cold start):

- Do not walk the tree
- Do not write skills

Forbidden in both modes:

- Writing skill sources into `.claude/skills` or `.agents/skills`
- Treating missing `.cs` / `Scripts` as "no modules"
- Generating before the user submits the multi-select
- Offering CastFlow / harness / adapter trees as skill-generation options
