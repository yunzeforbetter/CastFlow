"""Loader for the optional Jev module that lives in `<harness>/jev/`.

The implementation is not in this package. Cold start copies `jev/` into
`.castflow-runtime/jev/` only when the user checks the box.
"""

from __future__ import print_function

import os
import sys

_HARNESS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HARNESS not in sys.path:
    sys.path.insert(0, _HARNESS)

try:
    from jev.mark import *  # noqa: F401,F403
    from jev.mark import (  # explicit names for static readers
        NOTICE_NOT_CONFIGURED,
        OFFICIAL_SOURCE,
        apply_official_answer,
        build_evidence_cards,
        call_official_system_one,
        format_marks,
        key_path,
        mark_atoms,
        module_dir,
        official_config,
        prior_mark,
        questions_for_cards,
        read_project_key,
        review_mark,
        write_project_key,
    )
    AVAILABLE = True
except ImportError:
    AVAILABLE = False
    NOTICE_NOT_CONFIGURED = (
        "notice: Jev is not configured. Marking uses the structural prior."
    )
    OFFICIAL_SOURCE = "official-jev"

    def official_config(environ=None, project_root=None):
        return None

    def mark_atoms(atoms, edges, environ=None, client=None, project_root=None):
        del atoms, edges, environ, client, project_root
        return [], NOTICE_NOT_CONFIGURED

    def format_marks(marks):
        return "marks: {}\n".format(len(marks or []))

    def key_path(project_root):
        return os.path.join(project_root or "", ".castflow-runtime", "jev", "key")

    def module_dir(project_root):
        return ""

    def write_project_key(project_root, raw):
        return False

    def read_project_key(project_root):
        return None
