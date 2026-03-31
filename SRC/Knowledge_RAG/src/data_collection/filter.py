#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Dataset normalizer for CVE-related commits.

- Keeps only source-code files.
- Excludes tests (paths and common test DSLs).
- Removes comments/blank/trivial import/include/using lines.
- Splits multi-file commits into per-file cases.
- Emits unified added/deleted line buckets from a synthetic unified diff.

Usage:
    python tools/filter_dataset.py <input.json> <output.json>

Input:
  - Either a single CVE object with a "commits" array
  - Or a list of such CVE objects
See README for schema details.
"""

import json
import re
import difflib
import sys
from typing import Dict, List, Tuple, Any

# ---------------------------
# File/type filters
# ---------------------------

CODE_EXTENSIONS = (".c", ".cpp", ".cc", ".java", ".py", ".rb", ".go", ".js", ".ts", ".php")

TEST_PATH_PATTERNS = [
    re.compile(r"/test/", re.IGNORECASE),
    re.compile(r"/tests/", re.IGNORECASE),
    re.compile(r"/spec/", re.IGNORECASE),
    re.compile(r"/unittest/", re.IGNORECASE),
    re.compile(r"/__tests__/", re.IGNORECASE),
]

TEST_FILE_SUFFIXES = (".spec.", ".test.")

# Common test DSL identifiers across ecosystems (Ruby/RSpec, JS/Mocha/Jest, Python/pytest/unittest)
TEST_DSL_PATTERNS = [
    re.compile(r"\bRSpec\.describe\b"),
    re.compile(r"\bdescribe\b"),
    re.compile(r"\bit\b"),
    re.compile(r"\bcontext\b"),
    re.compile(r"class\s+.*Test\b"),
    re.compile(r"class\s+.*Spec\b"),
    re.compile(r"\bunittest\.TestCase\b"),
    re.compile(r"\bpytest\b"),
    re.compile(r"\bjest\b"),
    re.compile(r"\bmocha\b"),
]

COMMENT_OR_PUNCT_PREFIXES = ("//", "#", "/*", "*", "*/")


def is_code_file(file_path: str) -> bool:
    """Return True if the file has a recognized source extension."""
    return file_path.endswith(CODE_EXTENSIONS)


def is_test_file(file_path: str) -> bool:
    """Return True if the path or filename looks like a test file."""
    lower = file_path.lower()
    if any(p.search(lower) for p in TEST_PATH_PATTERNS):
        return True
    if lower.endswith(TEST_FILE_SUFFIXES):
        return True
    return False


def is_meaningful_line(line: str) -> bool:
    """
    Keep only lines that are not comments/blank/pure punctuation
    and are not trivial imports/includes/usings.
    """
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith(COMMENT_OR_PUNCT_PREFIXES):
        return False
    # Punctuation-only lines like { } ; () [] etc.
    if re.fullmatch(r"[{}\[\]();]+", stripped):
        return False
    # Trivial import/include/using
    if re.match(r"^(import|using|include)\b", stripped):
        return False
    return True


def is_test_dsl(line: str) -> bool:
    """Detect common test DSL tokens to further drop test-only lines."""
    return any(p.search(line) for p in TEST_DSL_PATTERNS)


# ---------------------------
# Patch helpers
# ---------------------------

def make_unified_patch(before: str, after: str) -> str:
    """Create a unified diff between normalized before/after code strings."""
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    diff = difflib.unified_diff(
        before_lines,
        after_lines,
        fromfile="code before",
        tofile="code after",
        lineterm=""
    )
    return "\n".join(diff)


def extract_added_deleted_from_patch(patch_text: str) -> Tuple[List[str], List[str]]:
    """
    Parse unified diff and return (added_lines, deleted_lines),
    ignoring diff headers.
    """
    added, deleted = [], []
    for line in patch_text.splitlines():
        if line.startswith(('+++', '---', '@@')):
            continue
        if line.startswith('+'):
            added.append(line[1:])
        elif line.startswith('-'):
            deleted.append(line[1:])
    return added, deleted


# ---------------------------
# Main transformation
# ---------------------------

def filter_commits(cve_obj: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Transform one CVE object into a list of per-file cases.
    Each case contains normalized code-before/after and added/deleted buckets.
    """
    out: List[Dict[str, Any]] = []

    for commit in cve_obj.get("commits", []):
        file_path = commit["file"]

        # File-level gating
        if not is_code_file(file_path):
            continue
        if is_test_file(file_path):
            continue

        # Normalize lines (drop noise & test DSL)
        before_lines = [
            l for l in commit.get("code_before_change", "").split("\n")
            if is_meaningful_line(l) and not is_test_dsl(l)
        ]
        after_lines = [
            l for l in commit.get("code_after_change", "").split("\n")
            if is_meaningful_line(l) and not is_test_dsl(l)
        ]

        # Skip empty/noisy diffs
        if not before_lines and not after_lines:
            continue

        before = "\n".join(before_lines)
        after = "\n".join(after_lines)

        # Build synthetic diff & extract changed lines
        patch_text = make_unified_patch(before, after)
        added, deleted = extract_added_deleted_from_patch(patch_text)

        out.append({
            "cve_id": cve_obj.get("cve_id", ""),
            "cwe": cve_obj.get("cwe", []),
            "cve_description": cve_obj.get("cve_description", ""),
            "file": file_path,
            "code_before_change": before,
            "code_after_change": after,
            "function_modified_lines": {
                "added": added,
                "deleted": deleted
            }
            # You can assign a deterministic "id" downstream if needed
        })

    return out


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python tools/filter_dataset.py <input.json> <output.json>")
        sys.exit(1)

    in_path, out_path = sys.argv[1], sys.argv[2]

    with open(in_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        cleaned: List[Dict[str, Any]] = []
        for item in data:
            cleaned.extend(filter_commits(item))
    else:
        cleaned = filter_commits(data)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

    print(f"Filtering completed Output: {out_path}  Cases: {len(cleaned)}")


if __name__ == "__main__":
    main()
