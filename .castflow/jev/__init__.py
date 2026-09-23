"""Optional Jev module. Not part of the core manager.

Cold start copies this directory to `.castflow-runtime/jev/` only when the
user checks the box. The API key lives in `key` inside that directory and is
gitignored. config.json stores the boolean only.
"""

from .mark import (  # noqa: F401
    NOTICE_NOT_CONFIGURED,
    OFFICIAL_SOURCE,
    OfficialConfig,
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
