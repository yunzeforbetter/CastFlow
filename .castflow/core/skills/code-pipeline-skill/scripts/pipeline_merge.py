#!/usr/bin/env python3
"""
code-pipeline-owned runtime merge script.

Merge Step 3 parallel agent outputs into PIPELINE_CONTEXT.md.

This script only projects Step 3 summaries back into the human-readable
pipeline context. It does not decide whether a pipeline may enter Step 3,
does not validate decision-state gates, and is not the runtime truth source.
Full details remain in the original files for on-demand reference by
subsequent pipeline steps.

This script belongs to code-pipeline's component-owned runtime binding.
It is not a generic framework merge primitive.

Zero external dependencies. Python 3.6+.

Usage:
    python .claude/skills/code-pipeline-skill/scripts/pipeline_merge.py
    python .claude/skills/code-pipeline-skill/scripts/pipeline_merge.py --dry-run
"""

import argparse
import os
import re
import sys


SUMMARY_PATTERN = re.compile(
    r"<!-- PIPELINE_SUMMARY -->\s*\n(.*?)\n\s*<!-- /PIPELINE_SUMMARY -->",
    re.DOTALL,
)
DETAIL_PATTERN = re.compile(
    r"<!-- PIPELINE_DETAIL -->\s*\n(.*?)\n\s*<!-- /PIPELINE_DETAIL -->",
    re.DOTALL,
)
PARENT_SUMMARY_PATTERN = re.compile(r"^\s*#{1,6}\s*Parent Summary\b", re.MULTILINE)

STEP3_MERGE_START = "<!-- PIPELINE_STEP3_MERGE_START -->"
STEP3_MERGE_END = "<!-- /PIPELINE_STEP3_MERGE_END -->"
STEP3_MERGE_BLOCK_PATTERN = re.compile(
    re.escape(STEP3_MERGE_START) + r".*?" + re.escape(STEP3_MERGE_END),
    re.DOTALL,
)

STEP3_INDEX_START = "<!-- PIPELINE_STEP3_INDEX_START -->"
STEP3_INDEX_END = "<!-- /PIPELINE_STEP3_INDEX_END -->"
STEP3_INDEX_BLOCK_PATTERN = re.compile(
    re.escape(STEP3_INDEX_START) + r".*?" + re.escape(STEP3_INDEX_END),
    re.DOTALL,
)


def extract_required_section(content, filename, section_name, pattern):
    matches = pattern.findall(content)
    if len(matches) != 1:
        if not matches:
            return None, "{} missing {} markers".format(filename, section_name)
        return None, "{} has {} {} blocks".format(filename, len(matches), section_name)
    return matches[0].strip(), None


def ensure_no_parent_summary(content, filename):
    if PARENT_SUMMARY_PATTERN.search(content):
        return "{} mixes Parent Summary into Step 3 output".format(filename)
    return None


def replace_or_append_managed_block(file_path, block_pattern, block, dry_run, label):
    with open(file_path, "r", encoding="utf-8-sig") as f:
        content = f.read()

    header, body = split_context_header(content)

    matches = list(block_pattern.finditer(body))
    if len(matches) > 1:
        print("Error: {} has {} managed {} blocks.".format(
            file_path, len(matches), label))
        sys.exit(1)

    if matches:
        new_body = block_pattern.sub(block, body, count=1)
        action = "replace"
    else:
        prefix = ""
        if body:
            prefix = "\n" if body.endswith("\n") else "\n\n"
        new_body = body + prefix + block
        action = "append"

    new_content = header + new_body

    if dry_run:
        print("\n--- Preview (would {} {}) ---".format(action, label))
        print(block)
        return

    with open(file_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(new_content)

    print("  [{}] {} -> {}".format(action.upper(), label, file_path))


def split_context_header(content):
    lines = content.splitlines(True)
    header_lines = []
    body_start = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "---":
            header_lines.append(line)
            body_start = i + 1
            break
        if stripped.startswith("pipeline_") or stripped == "" or stripped.startswith("# "):
            header_lines.append(line)
            continue
        body_start = i
        break
    else:
        body_start = len(lines)

    return "".join(header_lines), "".join(lines[body_start:])


def find_pipeline_root(start_dir):
    current = os.path.abspath(start_dir)
    while True:
        if os.path.isfile(os.path.join(current, "PIPELINE_CONTEXT.md")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def find_project_root():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidate = find_pipeline_root(script_dir)
    if candidate:
        return candidate

    cwd = os.getcwd()
    candidate = find_pipeline_root(cwd)
    if candidate:
        return candidate

    print("Error: PIPELINE_CONTEXT.md not found.")
    print("  Searched upward from script dir: {}".format(script_dir))
    print("  Searched upward from cwd: {}".format(os.path.abspath(cwd)))
    sys.exit(1)


def collect_outputs(output_dir):
    if not os.path.isdir(output_dir):
        print("Error: {} does not exist.".format(output_dir))
        sys.exit(1)

    files = sorted(
        f for f in os.listdir(output_dir)
        if f.endswith(".md")
    )

    if not files:
        print("Error: No .md files found in {}.".format(output_dir))
        print("Step 3 outputs are required before Step 4 / Step 5 may continue.")
        sys.exit(1)

    entries = []
    errors = []
    for filename in files:
        path = os.path.join(output_dir, filename)
        with open(path, "r", encoding="utf-8-sig") as f:
            content = f.read()

        module_id = filename.replace(".md", "")
        summary, summary_error = extract_required_section(
            content, filename, "PIPELINE_SUMMARY", SUMMARY_PATTERN,
        )
        detail, detail_error = extract_required_section(
            content, filename, "PIPELINE_DETAIL", DETAIL_PATTERN,
        )
        parent_summary_error = ensure_no_parent_summary(content, filename)

        if summary_error:
            errors.append(summary_error)
        if detail_error:
            errors.append(detail_error)
        if parent_summary_error:
            errors.append(parent_summary_error)
        if summary_error or detail_error or parent_summary_error:
            continue

        print("  [READ]   {} -> summary/detail verified ({} / {} chars)".format(
            filename, len(summary), len(detail)))

        entries.append((module_id, summary))

    if errors:
        print("\nError: invalid Step 3 outputs detected. Refusing merge.")
        for error in errors:
            print("  - {}".format(error))
        print("Expected markers are defined by code-pipeline protocol.")
        sys.exit(1)

    return entries


def append_to_context(context_path, entries, output_dir, dry_run):
    step3_block = (
        STEP3_MERGE_START +
        "\n## Step 3: Module Implementation Results\n" +
        "\nDetail files: `temp/pipeline-output/`\n"
    )

    for module_id, summary in entries:
        step3_block += "\n{}\n".format(summary)

    step3_block += "\n---\n" + STEP3_MERGE_END + "\n"
    replace_or_append_managed_block(
        context_path, STEP3_MERGE_BLOCK_PATTERN, step3_block, dry_run, "Step 3 merge block",
    )


def update_index(index_path, context_path, entries, dry_run):
    if not os.path.isfile(index_path):
        return

    with open(context_path, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()

    step3_line = None
    for i, line in enumerate(lines):
        if line.strip() == STEP3_MERGE_START:
            step3_line = i + 2
            break
        if line.strip().startswith("## Step 3"):
            step3_line = i + 1
            break

    if step3_line is None:
        return

    index_entries = [
        STEP3_INDEX_START + "\n",
        "- Step 3 (Module Implementation): line {}\n".format(step3_line),
    ]
    for module_id, _ in entries:
        index_entries.append("  - {}: temp/pipeline-output/{}.md\n".format(module_id, module_id))
    index_entries.append(STEP3_INDEX_END + "\n")
    index_block = "".join(index_entries)
    replace_or_append_managed_block(
        index_path, STEP3_INDEX_BLOCK_PATTERN, index_block, dry_run, "Step 3 index block",
    )


def main():
    parser = argparse.ArgumentParser(
        description="Merge code-pipeline Step 3 outputs into PIPELINE_CONTEXT.md",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview without writing",
    )
    args = parser.parse_args()

    project_root = find_project_root()
    output_dir = os.path.join(project_root, "temp", "pipeline-output")
    context_path = os.path.join(project_root, "PIPELINE_CONTEXT.md")
    index_path = os.path.join(project_root, "PIPELINE_INDEX.md")

    print("Project root: {}".format(project_root))
    print("Output dir:   {}".format(output_dir))

    print("\n=== Collecting Step 3 outputs ===")
    entries = collect_outputs(output_dir)

    print("\n=== Merging summaries to PIPELINE_CONTEXT.md ===")
    append_to_context(context_path, entries, output_dir, args.dry_run)
    update_index(index_path, context_path, entries, args.dry_run)

    print("\n=== Done ({} module(s) merged) ===".format(len(entries)))
    print("Full details remain in: {}".format(output_dir))


if __name__ == "__main__":
    main()
