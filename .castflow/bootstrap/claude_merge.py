"""CLAUDE.md merging strategies.

Three merge paths:
1. Has boundary marker -> replace harness section, keep project section
2. No marker -> section-level semantic dedup + append unique sections
3. Harness diff -> interactive choice (template / keep / merge)
"""

import difflib
import re
import os

from .io_ops import read_file, safe_write

CLAUDE_BOUNDARY = "<!-- =========="

_YAML_FRONT = re.compile(r"\A---\n.*?\n---\n*", re.DOTALL)

EMOJI_CHARS = set(
    "\u274c\u2705\u2b50\U0001f4cb\U0001f534\U0001f7e1\U0001f7e2"
    "\u2713\u2717\u2192\u2194\u2190\u2193\u2191"
    "\u25ba\u25bc\u25b2\u25c4\u25c6\u2605"
)


def _split_at_boundary(content):
    if CLAUDE_BOUNDARY in content:
        idx = content.index(CLAUDE_BOUNDARY)
        return content[:idx], content[idx:]
    return content, ""


def _extract_sections(content):
    """Split markdown into sections by ## headings, stripping YAML frontmatter."""
    stripped = _YAML_FRONT.sub("", content, count=1)
    sections = []
    heading = ""
    body_lines = []

    for line in stripped.split("\n"):
        if line.startswith("## "):
            if heading or body_lines:
                sections.append((heading, "\n".join(body_lines).strip()))
            heading = line
            body_lines = []
        else:
            body_lines.append(line)

    if heading or body_lines:
        sections.append((heading, "\n".join(body_lines).strip()))

    return sections


def _normalize_for_compare(text):
    """Normalize text for similarity comparison."""
    for ch in EMOJI_CHARS:
        text = text.replace(ch, "")
    text = text.replace("\u2192", "->")
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _deduplicate_sections(existing, new_content, threshold=0.50):
    """Find sections in existing that have no close match in new_content."""
    old_sections = _extract_sections(existing)
    new_sections = _extract_sections(new_content)

    if not old_sections:
        return []

    new_normalized = []
    for h, b in new_sections:
        full = "{}\n{}".format(h, b).strip()
        new_normalized.append(_normalize_for_compare(full))

    unique = []
    for old_h, old_b in old_sections:
        old_full = "{}\n{}".format(old_h, old_b).strip()
        if not old_full:
            continue

        old_norm = _normalize_for_compare(old_full)
        if not old_norm:
            continue

        best_ratio = 0.0
        for new_norm in new_normalized:
            ratio = difflib.SequenceMatcher(None, old_norm, new_norm).ratio()
            if ratio > best_ratio:
                best_ratio = ratio

        label = old_h[:60] if old_h else "(preamble)"
        safe_label = label.encode("ascii", "replace").decode("ascii")
        if best_ratio < threshold:
            unique.append((old_h, old_b))
            print("  [UNIQUE]  {} (best {:.0f}%)".format(safe_label, best_ratio * 100))
        else:
            print("  [DUP]     {} ({:.0f}% match, skipped)".format(
                safe_label, best_ratio * 100))

    return unique


def _extract_user_additions(old_harness, new_harness):
    old_lines = old_harness.strip().splitlines()
    new_lines = new_harness.strip().splitlines()
    new_set = set(line.strip() for line in new_lines if line.strip())

    additions = []
    for line in old_lines:
        if line.strip() and line.strip() not in new_set:
            additions.append(line)

    return "\n".join(additions) if additions else ""


def _default_choice_callback(prompt_text):
    """Default interactive prompt for merge decisions."""
    while True:
        try:
            choice = input(prompt_text).strip()
        except (EOFError, KeyboardInterrupt):
            return None
        if choice in ("1", "2", "3"):
            return choice
        print("  Please enter 1, 2, or 3.")


def merge_claude_md(dest_path, new_content, dry_run, backup_session=None,
                    choice_callback=None):
    """Merge new CLAUDE.md content with existing file.

    Args:
        choice_callback: callable(prompt_text) -> "1"|"2"|"3"|None.
            Defaults to interactive input(). Inject a stub for testing.
    """
    if choice_callback is None:
        choice_callback = _default_choice_callback

    if not os.path.isfile(dest_path):
        safe_write(dest_path, new_content, "full", dry_run, backup_session)
        return

    existing = read_file(dest_path)

    old_harness, old_project = _split_at_boundary(existing)
    new_harness, new_project = _split_at_boundary(new_content)

    if not old_project:
        print("  [MIGRATE] Existing CLAUDE.md has no boundary marker.")
        print("            Scanning for unique sections to preserve...")

        unique = _deduplicate_sections(existing, new_content)

        if unique:
            parts = []
            for h, b in unique:
                section = "{}\n\n{}".format(h, b).strip() if h else b.strip()
                parts.append(section)
            unique_text = "\n\n---\n\n".join(parts)

            new_harness_part, new_project_part = _split_at_boundary(new_content)
            if new_project_part:
                merged = new_harness_part + new_project_part.rstrip("\n") + \
                    "\n\n" + unique_text + "\n"
            else:
                merged = new_content.rstrip("\n") + "\n\n" + unique_text + "\n"
            print("  [MERGE]   {} unique section(s) appended to project section.".format(
                len(unique)))
        else:
            merged = new_content
            print("  [CLEAN]   All existing content covered by template. Using template as-is.")

        if not dry_run:
            backup_path = dest_path + ".migrate-backup"
            with open(backup_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(existing)
            print("  [BACKUP]  Original saved to {}".format(
                os.path.basename(backup_path)))
        safe_write(dest_path, merged, "full", dry_run, backup_session)
        return

    if old_harness.strip() == new_harness.strip():
        print("  [MATCH]   Harness section unchanged, project section preserved.")
        merged = new_harness + old_project
        safe_write(dest_path, merged, "full", dry_run, backup_session)
        return

    similarity = difflib.SequenceMatcher(
        None, old_harness.strip(), new_harness.strip()
    ).ratio()
    pct = int(similarity * 100)

    print("  [DIFF]    Harness section differs from template ({}% similar).".format(pct))

    if dry_run:
        print("            (dry-run: would prompt for merge decision)")
        return

    print("")
    print("  Your CLAUDE.md harness section has modifications.")
    print("  Options:")
    print("    1 - Use template version (recommended: keeps framework rules up to date)")
    print("        Your old harness section will be saved to CLAUDE.md.castflow-backup")
    print("    2 - Keep your current version (skip harness update)")
    print("    3 - Merge: use template version + append your differences to project section")
    print("")

    choice = choice_callback("  Choose [1/2/3]: ")
    if choice is None:
        print("\n  Cancelled. CLAUDE.md not modified.")
        return

    if choice == "1":
        backup_path = dest_path + ".castflow-backup"
        with open(backup_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(old_harness)
        print("  [BACKUP]  Old harness section saved to {}".format(
            os.path.basename(backup_path)))
        merged = new_harness + old_project
        safe_write(dest_path, merged, "full", False, backup_session)

    elif choice == "2":
        print("  [SKIP]    CLAUDE.md harness section not updated.")

    elif choice == "3":
        backup_path = dest_path + ".castflow-backup"
        with open(backup_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(old_harness)
        print("  [BACKUP]  Old harness section saved to {}".format(
            os.path.basename(backup_path)))

        user_diff = _extract_user_additions(old_harness, new_harness)
        if user_diff:
            merged_project = old_project.rstrip("\n") + "\n\n" + \
                "## Migrated from harness section\n\n" + \
                "<!-- The following content was in your harness section but differs from template. -->\n" + \
                "<!-- Review and reorganize as needed, then remove this comment. -->\n\n" + \
                user_diff + "\n"
            merged = new_harness + merged_project
            print("  [MERGE]   Template harness applied. Your modifications appended to project section.")
        else:
            merged = new_harness + old_project
            print("  [MERGE]   No unique user additions detected. Template harness applied.")
        safe_write(dest_path, merged, "full", False, backup_session)
