"""Manifest loading and validation."""

import json
import os
import sys

from .paths import BOOTSTRAP_OUTPUT

SUPPORTED_VERSIONS = [1]


def load_manifest(project_root):
    """Load and validate bootstrap-output/manifest.json."""
    manifest_path = os.path.join(project_root, BOOTSTRAP_OUTPUT, "manifest.json")

    if not os.path.isfile(manifest_path):
        print("Error: Manifest not found at {}".format(manifest_path))
        print("  AI must generate {}/manifest.json first.".format(BOOTSTRAP_OUTPUT))
        sys.exit(1)

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
