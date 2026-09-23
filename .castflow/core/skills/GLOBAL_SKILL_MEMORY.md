---
name: global-skill-memory
description: >
  Runtime API-evidence and constraint overlay for an already-active
  catalog skill.
---

# GLOBAL_SKILL_MEMORY

Runtime protocol for a catalog skill that is already active.

**Load**: protocols 1-3 stay in force. Whether to write code is protocol 3 only.

---

## Protocol 1: Prove a project API before use

Training data and "the usual way" are not this repository. A project or module API needs evidence before it enters a patch.

Any one of these is enough:

1. A real usage in the current skill's EXAMPLES.md
2. An opened source definition (the signature of that symbol; a neighboring method is not verified)
3. A location the user pointed at

A Grep hit does not mean this type has this method.

Skip this gate for language and standard-library APIs, and for the same symbol with the same signature already written in the file you are editing. A new name, a new arity, or a new overload still needs evidence.

Unverified project API: mark that call TODO and keep writing the rest. Do not invent a signature. Do not assume B has a method because A does.

---

## Protocol 2: Constraints beat copied code

A finished implementation is easy to copy together with its local anti-patterns.

Copied code yields to constraints. Sources, in the order you consult them: the current skill's `SKILL_MEMORY.md`, injected root rules (`CLAUDE.md` / `AGENTS.md`), and this file. If this file conflicts with the injected root rules, the root rules win.

---

## Protocol 3: If the scope is unclear, ask first

Vague requirement or unclear blast radius: collect first; do not write code.
Irreversible: state the risk and wait for confirmation before writing.
Everything else, including a large but reversible change, implement directly. Do not announce an execution mode. Do not add a confirmation gate to an ordinary patch.
