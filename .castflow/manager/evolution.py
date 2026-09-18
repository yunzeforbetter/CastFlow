"""Evolution plugin: one-switch enable/disable.

Wave A only persists the flag. Adapter uninstall (hooks / origin-evolve
projection) is applied by adapters.sync when that layer exists; calling
set_enabled is still the single public API both CLI and UI must use.
"""

from .config import load_config, set_evolution


def is_enabled(project_root):
    return bool(load_config(project_root).get("evolution", {}).get("enabled", True))


def set_enabled(project_root, enabled, sync_fn=None):
    """Turn evolution on or off.

    sync_fn(project_root, config) is optional; Wave B+ passes adapters.sync
    so hooks and origin-evolve projection follow the flag.
    """
    config = set_evolution(project_root, enabled)
    if sync_fn is not None:
        sync_fn(project_root, config)
    return config
