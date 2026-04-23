#!/usr/bin/env python3
"""
Merge Step 3 parallel agent outputs into PIPELINE_CONTEXT.md.

Reads all .md files from temp/pipeline-output/, extracts the
PIPELINE_SUMMARY section from each, and appends summaries to
PIPELINE_CONTEXT.md. Full details remain in the original files
for on-demand reference by subsequent pipeline steps.

Zero external dependencies. Python 3.6+.

Usage:
    python .claude/scripts/pipeline_merge.py
    python .claude/scripts/pipeline_merge.py --dry-run
"""

import argparse
import os
import re
import sys


SUMMARY_PATTERN = re.compile(
    r"<!-- PIPELINE_SUMMARY -->\s*\n(.*?)\n\s*<!-- /PIPELINE_SUMMARY -->",
    re.DOTALL,
)


def find_project_root():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.dirname(os.path.dirname(script_dir))

    if os.path.isfile(os.path.join(candidate, "PIPELINE_CONTEXT.md")):
        return candidate

    cwd = os.getcwd()
    if os.path.isfile(os.path.join(cwd, "PIPELINE_CONTEXT.md")):
        return cwd

    print("Error: PIPELINE_CONTEXT.md not found.")
    print("  Searched: {}".format(candidate))
    print("  Searched: {}".format(cwd))
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
        print("Warning: No .md files found in {}.".format(output_dir))
        return []

    entries = []
    for filename in files:
        path = os.path.join(output_dir, filename)
        with open(path, "r", encoding="utf-8-sig") as f:
            content = f.read()

        module_id = filename.replace(".md", "")
        match = SUMMARY_PATTERN.search(content)

        if match:
            summary = match.group(1).strip()
            print("  [READ]   {} -> summary ({} chars)".format(filename, len(summary)))
        else:
            summary = content.strip()
            print("  [READ]   {} -> no PIPELINE_SUMMARY markers, using full content ({} chars)".format(
                filename, len(summary)))

        entries.append((module_id, summary))

    return entries


def append_to_context(context_path, entries, output_dir, dry_run):
    step3_block = "\n\n## Step 3: Module Implementation Results\n"
    step3_block += "\nDetail files: `temp/pipeline-output/`\n"

    for module_id, summary in entries:
        step3_block += "\n{}\n".format(summary)

    step3_block += "\n---\n"

    if dry_run:
        print("\n--- Preview (would append to PIPELINE_CONTEXT.md) ---")
        print(step3_block)
        return

    with open(context_path, "a", encoding="utf-8", newline="\n") as f:
        f.write(step3_block)

    print("  [APPEND] {} module(s) -> PIPELINE_CONTEXT.md".format(len(entries)))


def update_index(index_path, context_path, entries, dry_run):
    if not os.path.isfile(index_path):
        return

    with open(context_path, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()

    step3_line = None
    for i, line in enumerate(lines):
        if line.strip().startswith("## Step 3"):
            step3_line = i + 1
            break

    if step3_line is None:
        return

    index_entries = ["- Step 3 (Module Implementation): line {}\n".format(step3_line)]
    for module_id, _ in entries:
        index_entries.append("  - {}: temp/pipeline-output/{}.md\n".format(module_id, module_id))

    if dry_run:
        for entry in index_entries:
            print("  [INDEX]  Would add: {}".format(entry.strip()))
        return

    with open(index_path, "a", encoding="utf-8", newline="\n") as f:
        f.writelines(index_entries)

    print("  [INDEX]  Updated PIPELINE_INDEX.md")


def main():
    parser = argparse.ArgumentParser(
        description="Merge Step 3 outputs into PIPELINE_CONTEXT.md",
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

    if not entries:
        print("\nNothing to merge.")
        return

    print("\n=== Merging summaries to PIPELINE_CONTEXT.md ===")
    append_to_context(context_path, entries, output_dir, args.dry_run)
    update_index(index_path, context_path, entries, args.dry_run)

    print("\n=== Done ({} module(s) merged) ===".format(len(entries)))
    print("Full details remain in: {}".format(output_dir))


if __name__ == "__main__":
    main()
