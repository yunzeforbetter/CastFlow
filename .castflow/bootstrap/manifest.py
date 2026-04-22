"""Manifest loading and validation."""

import json
import os
import sys

from .paths import BOOTSTRAP_OUTPUT

SUPPORTED_VERSIONS = [1]

# CastFlow bootstrap manifest only — avoids clashing with Unity Packages/manifest.json
# or other project-root manifests. Legacy filename still read for migration.
CF_MANIFEST_FILENAME = "cf_manifest.json"
MANIFEST_LEGACY_FILENAME = "manifest.json"


def get_manifest_path(project_root):
    """Absolute path to bootstrap-output/cf_manifest.json (canonical)."""
    return os.path.join(project_root, BOOTSTRAP_OUTPUT, CF_MANIFEST_FILENAME)


def get_legacy_manifest_path(project_root):
    """Absolute path to deprecated bootstrap-output/manifest.json."""
    return os.path.join(project_root, BOOTSTRAP_OUTPUT, MANIFEST_LEGACY_FILENAME)


def resolve_manifest_path(project_root):
    """Return path to an existing manifest file, or None. Prefers cf_manifest.json."""
    cf = get_manifest_path(project_root)
    if os.path.isfile(cf):
        return cf
    legacy = get_legacy_manifest_path(project_root)
    if os.path.isfile(legacy):
        return legacy
    return None


def write_minimal_manifest(
    project_root,
    language="zh",
    tech_stack="unity",
    profile="standard",
    merge_mode="full",
):
    """Create bootstrap-output/ and a minimal cf_manifest.json if missing.

    Used by CLI --init-manifest for non-interactive bootstrap. Full init with
    Phase 0 language selection and rich content is still owned by bootstrap-skill.
    """
    out_dir = os.path.join(project_root, BOOTSTRAP_OUTPUT)
    os.makedirs(out_dir, exist_ok=True)
    manifest_path = get_manifest_path(project_root)
    if os.path.isfile(manifest_path):
        print("  [SKIP]    {} already exists (not overwriting).".format(
            manifest_path))
        return False
    legacy_path = get_legacy_manifest_path(project_root)
    if os.path.isfile(legacy_path):
        print("  [SKIP]    {} exists (legacy). Not creating {}. "
              "Rename legacy file to cf_manifest.json when ready.".format(
                  legacy_path, manifest_path))
        return False
    data = {
        "version": 1,
        "tech_stack": tech_stack,
        "language": language,
        "profile": profile,
        "merge_mode": merge_mode,
        "modules": [],
        "optional_skills": {"debug": True, "profiler": True},
        "naming_conventions": "",
    }
    with open(manifest_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("  [CREATE]  {}".format(manifest_path))
    print("            language={} (edit file or re-run bootstrap-skill to align with Phase 0).".format(
        language))
    return True


def load_manifest(project_root):
    """Load and validate bootstrap-output/cf_manifest.json (or legacy manifest.json)."""
    manifest_path = resolve_manifest_path(project_root)

    if not manifest_path:
        canonical = get_manifest_path(project_root)
        print("Error: CastFlow manifest not found at {}".format(canonical))
        print("  (Legacy bootstrap-output/manifest.json is still accepted if present.)")
        print("  Either:")
        print("    (1) Follow bootstrap-skill: Phase 0 language + manifest, then run this script; or")
        print("    (2) py -3 CastFlow/.castflow/bootstrap.py --init-manifest --language zh")
        sys.exit(1)

    if os.path.basename(manifest_path) == MANIFEST_LEGACY_FILENAME:
        print("  [NOTE]    Using legacy {} — prefer renaming to {}.".format(
            manifest_path, CF_MANIFEST_FILENAME))

    with open(manifest_path, "r", encoding="utf-8-sig") as f:
        manifest = json.load(f)

    version = manifest.get("version")
    if version not in SUPPORTED_VERSIONS:
        print("Error: Manifest version {} not supported (expected {}).".format(
            version, SUPPORTED_VERSIONS))
        sys.exit(1)

    if "modules" not in manifest:
        print("Error: Manifest missing 'modules' field.")
        sys.exit(1)

    seen_ids = set()
    for i, mod in enumerate(manifest["modules"]):
        if "id" not in mod:
            print("Error: Module at index {} missing 'id'.".format(i))
            sys.exit(1)
        if "display_name" not in mod:
            print("Error: Module '{}' missing 'display_name'.".format(mod["id"]))
            sys.exit(1)
        if mod["id"] in seen_ids:
            print("Error: Duplicate module id '{}'.".format(mod["id"]))
            sys.exit(1)
        seen_ids.add(mod["id"])

    return manifest
