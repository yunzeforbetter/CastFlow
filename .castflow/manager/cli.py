"""CastFlow manager CLI: seed / ui / sync / evolve / queue / flush."""

from __future__ import print_function

import argparse
import json
import os
import sys

from . import adapters, catalog, config, evolution, queue, setup, skills
from .paths import (
    FactoryRuntimeError,
    find_harness_dir,
    find_project_root,
    runtime_dir,
)


USAGE = """
CastFlow manager

  castflow.bat                          # Windows: guided cold-start wizard
  ./castflow.sh                         # macOS / Linux: same wizard (or double-click castflow.command)
  python .castflow/manager.py launch    # CastFlow checkout: same GUI (any OS)
  python .castflow-runtime/manager.py   # seeded project: ui / sync / validate / ...
  python .castflow/manager.py setup     # headless: config + seed + sync
  python .castflow/manager.py unseed    # remove runtime/projections; wizard can run again
  python .castflow/manager.py seed      # runtime + core skills on Claude/.agents discovery paths
  python .castflow/manager.py ui        # visual console (127.0.0.1)
  python .castflow/manager.py skills    # list inventoried runtime skills
  python .castflow/manager.py retire NAME
  python .castflow/manager.py activate NAME
  python .castflow/manager.py update NAME
  python .castflow/manager.py sync      # project non-retired runtime skills to adapter trees
  python .castflow/manager.py evolve on|off
  python .castflow/manager.py queue     # enqueue accepted modules for AI
  python .castflow/manager.py handoff   # print the next skill-creator prompt
  python .castflow/manager.py flush     # run trace-flush (Codex / no Stop hook)
  python .castflow/manager.py homology  # batch connected-component homology (stdin JSON)
  python .castflow/manager.py validate  # four-file check on runtime skills

Cold start is the GUI (castflow.bat / castflow.sh / launch), not an AI conversation.
Steps: configure -> optional scan/generate prompt -> 开启冷启动 (copy files) -> if checked, paste prompt.
Framework update refreshes CastFlow source skills and core files; it never overwrites project skills.
"""


def _print_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_seed(project_root, args):
    try:
        report = adapters.seed(project_root, dry_run=args.dry_run)
    except FactoryRuntimeError as exc:
        print(exc)
        return 2
    print("Runtime: {}".format(runtime_dir(project_root)))
    print("Seed complete. Next: python .castflow-runtime/manager.py ui")
    if args.verbose:
        _print_json(report)
    return 0


def cmd_sync(project_root, args):
    report = adapters.sync(project_root, dry_run=args.dry_run)
    print("Sync complete. Evolution={}".format(report.get("evolution")))
    if args.verbose:
        _print_json(report)
    return 0


def cmd_skills(project_root, args):
    items = skills.inventory(project_root)
    if args.verbose:
        _print_json(items)
        return 0
    if not items:
        print("No skills in runtime store. Run: python .castflow/manager.py seed")
        return 0
    print("{:28} {:12} {:8} {}".format("NAME", "KIND", "STATUS", "ROLE"))
    for item in items:
        status = "retired" if item.get("retired") else "active"
        role = item.get("role") or ""
        print("{:28} {:12} {:8} {}".format(
            item["name"], item["kind"], status, role))
    print("{} skill(s)".format(len(items)))
    return 0


def cmd_retire(project_root, args):
    result = skills.retire(project_root, args.name)
    if not result.get("ok"):
        print("retire failed: {}".format(result.get("error") or "unknown error"))
        return 2
    adapters.refresh_projections(project_root)
    print("Disabled {} on this machine and refreshed projections.".format(args.name))
    if args.verbose:
        _print_json(result)
    return 0


def cmd_activate(project_root, args):
    result = skills.restore(project_root, args.name)
    if not result.get("ok"):
        print("activate failed: {}".format(result.get("error") or "unknown error"))
        return 2
    adapters.refresh_projections(project_root)
    print("Enabled {} on this machine and refreshed projections.".format(args.name))
    if args.verbose:
        _print_json(result)
    return 0


def cmd_update(project_root, args):
    result = skills.update_skill(project_root, args.name)
    if not result.get("ok"):
        print("update failed: {}".format(result.get("error") or "unknown error"))
        return 2
    print("Updated {} from source of truth.".format(args.name))
    if args.verbose:
        _print_json(result)
    return 0


def cmd_evolve(project_root, args):
    if args.state is None:
        on = evolution.is_enabled(project_root)
        print("evolution: {}".format("on" if on else "off"))
        return 0
    enabled = args.state in ("on", "enable", "true", "1")
    if args.state in ("off", "disable", "false", "0"):
        enabled = False
    elif args.state not in ("on", "enable", "true", "1"):
        print("Usage: manager.py evolve on|off")
        return 2
    evolution.set_enabled(project_root, enabled, sync_fn=adapters.sync)
    print("evolution: {}".format("on" if enabled else "off"))
    return 0


def cmd_queue(project_root, args):
    data = queue.enqueue_accepted(project_root)
    print("Queued {} item(s).".format(len(data.get("items") or [])))
    print(queue.build_handoff(project_root))
    return 0


def cmd_handoff(project_root, args):
    print(queue.build_handoff(project_root))
    return 0


def cmd_flush(project_root, args):
    import subprocess
    from .paths import hooks_dir_for
    script = os.path.join(hooks_dir_for(project_root), "trace-flush.py")
    return subprocess.call([sys.executable, script], cwd=project_root)


def cmd_homology(project_root, args):
    """Batch homology CLI. Reads JSON items on stdin, prints clusters."""
    from .paths import hooks_dir_for
    hooks = hooks_dir_for(project_root)
    if hooks not in sys.path:
        sys.path.insert(0, hooks)
    import _homology
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    items = data.get("items") if isinstance(data, dict) else []
    result = _homology.cluster_items(items or [])
    json.dump(result, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


def cmd_validate(project_root, args):
    from installer.validate import validate_all
    return 0 if validate_all(project_root) else 1


def cmd_status(project_root, args):
    _print_json({
        "project_root": project_root,
        "runtime": runtime_dir(project_root),
        "config": config.load_config(project_root),
        "catalog": catalog.load_catalog(project_root),
        "queue": queue.load_queue(project_root),
        "adapters": adapters.adapter_status(project_root),
        "skills": skills.inventory(project_root),
        "retired": sorted(skills.retired_names(project_root)),
    })
    return 0


def cmd_setup(project_root, args):
    options = {}
    if getattr(args, "language", None):
        options["language"] = args.language
    if getattr(args, "generate_skills", False):
        options["generate_skills"] = True
    try:
        report = setup.cold_start(project_root, options)
    except FactoryRuntimeError as exc:
        print(exc)
        return 2
    print("Cold start complete. Seeded={} modules={} queued={}".format(
        report.get("seeded"), report.get("modules"), report.get("queued")))
    print("Runtime: {}".format(runtime_dir(project_root)))
    handoff = report.get("handoff") or ""
    if handoff:
        print("Next: paste this in Claude / Grok / Codex:")
        print(handoff)
    else:
        print("Framework copied. No AI prompt (scan/generate was not requested).")
    if args.verbose:
        _print_json({
            "seeded": report.get("seeded"),
            "modules": report.get("modules"),
            "config": report.get("config"),
        })
    return 0


def cmd_unseed(project_root, args):
    try:
        report = setup.unseed(project_root)
    except FactoryRuntimeError as exc:
        print(exc)
        return 2
    print("Unseeded. Seeded={}".format(report.get("seeded")))
    print("Removed {} path(s). Run setup / launch to cold-start again.".format(
        len(report.get("removed") or [])))
    if args.verbose:
        _print_json(report)
    return 0


def cmd_update_framework(project_root, args):
    report = setup.update_framework(project_root)
    print("Framework updated: {}".format(
        ", ".join(report.get("updated") or []) or "(none)"))
    if args.verbose:
        _print_json(report)
    return 0


def cmd_launch(project_root, args):
    explicit = getattr(args, "project_root", None)
    harness = getattr(args, "from_harness", None)
    suggested = project_root
    if harness:
        suggested = setup.resolve_launch_root(
            explicit=explicit,
            harness_checkout=harness,
        )
    if explicit:
        root = os.path.abspath(explicit)
    elif getattr(args, "no_picker", False):
        root = suggested
    else:
        print("Select the game/app folder. CastFlow can live in another directory.")
        picked = setup.pick_project_directory(
            suggested, "Select the project folder to install CastFlow")
        if not picked:
            print("No folder selected.")
            return 1
        root = picked
    seeded = setup.is_seeded(root)
    print("Project: {}".format(root))
    print("CastFlow: {}".format(os.path.dirname(find_harness_dir())))
    print("Seeded: {}".format("yes" if seeded else "no (setup wizard)"))
    setup.print_launch_guide(seeded=seeded)
    from .ui.server import serve
    return serve(root, port=args.port, no_browser=args.no_browser)


def cmd_ui(project_root, args):
    from .ui.server import serve
    return serve(project_root, port=args.port, no_browser=args.no_browser)


def build_parser():
    parser = argparse.ArgumentParser(
        description="CastFlow manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=USAGE,
    )
    parser.add_argument("--project-root", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("seed", help="Create runtime and project core files")
    sub.add_parser("sync", help="Project non-retired skills and hooks to adapter trees")
    sub.add_parser("skills", help="List inventoried runtime skills")
    p_ret = sub.add_parser("retire", help="Retire a skill (excluded from later sync)")
    p_ret.add_argument("name")
    p_act = sub.add_parser("activate", help="Re-enable a retired skill and sync")
    p_act.add_argument("name")
    p_upd = sub.add_parser("update", help="Refresh a skill from its source of truth into runtime")
    p_upd.add_argument("name")
    p_evo = sub.add_parser("evolve", help="Enable/disable the evolution plugin")
    p_evo.add_argument("state", nargs="?", default=None)
    sub.add_parser("queue", help="Enqueue accepted modules for sequential AI generation")
    sub.add_parser("handoff", help="Print the next skill-creator prompt")
    sub.add_parser("flush", help="Run trace-flush once")
    sub.add_parser("homology", help="Batch MEMORY homology (stdin JSON items)")
    sub.add_parser("status", help="Dump config/catalog/queue as JSON")
    sub.add_parser("validate", help="Validate four-file skills in runtime")
    p_ui = sub.add_parser("ui", help="Open the visual console")
    p_ui.add_argument("--port", type=int, default=8765)
    p_ui.add_argument("--no-browser", action="store_true")
    p_launch = sub.add_parser("launch", help="Open GUI; unseeded projects get the setup wizard")
    p_launch.add_argument("--port", type=int, default=8765)
    p_launch.add_argument("--no-browser", action="store_true")
    p_launch.add_argument(
        "--from-harness", default=None,
        help="CastFlow checkout dir (set by castflow.bat / castflow.sh) to resolve submodule vs clone",
    )
    p_launch.add_argument(
        "--no-picker", action="store_true",
        help="Do not open the folder picker (use --project-root or heuristic)",
    )
    p_setup = sub.add_parser("setup", help="Headless cold start: config + seed + sync")
    p_setup.add_argument("--language", default=None)
    p_setup.add_argument(
        "--generate-skills", action="store_true",
        help="Return the /goal loop-engine prompt after copying framework files",
    )
    sub.add_parser("unseed", help="Remove runtime and projections so cold start can run again")
    sub.add_parser("update-framework", help="Refresh CastFlow source skills and core files, then sync")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    project_root = find_project_root(args.project_root)

    if not args.cmd:
        print("Project root: {}".format(project_root))
        print(USAGE)
        return 0

    dispatch = {
        "seed": cmd_seed,
        "sync": cmd_sync,
        "skills": cmd_skills,
        "retire": cmd_retire,
        "activate": cmd_activate,
        "update": cmd_update,
        "evolve": cmd_evolve,
        "queue": cmd_queue,
        "handoff": cmd_handoff,
        "flush": cmd_flush,
        "homology": cmd_homology,
        "status": cmd_status,
        "validate": cmd_validate,
        "ui": cmd_ui,
        "launch": cmd_launch,
        "setup": cmd_setup,
        "unseed": cmd_unseed,
        "update-framework": cmd_update_framework,
    }
    try:
        return dispatch[args.cmd](project_root, args)
    except FactoryRuntimeError as exc:
        print(exc)
        return 2
