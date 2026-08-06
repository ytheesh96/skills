#!/usr/bin/env python3
"""Deterministic checks for the Hermes flat skill tap."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "hermes-skill-manifest.json"
RETIRED = re.compile(
    r"delegate_task\s*\(\s*mode\s*=\s*['\"](?:loop|durable)['\"]|"
    r"\b(?:loop_graph|loop_create|loop_status|loop_block)\s*\("
)
REQUIRED_ORCHESTRATION = (
    "kanban_create", "kanban_list", "kanban_show", "kanban_block",
    "kanban_unblock", "kanban_link", "board", "tenant",
)


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        raise ValueError("missing YAML frontmatter opening marker")
    end = text.find("\n---", 4)
    if end < 0:
        raise ValueError("missing YAML frontmatter closing marker")
    values: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if not line.strip() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"\'')
    if not values.get("name") or not values.get("description"):
        raise ValueError("frontmatter requires name and description")
    return values


def fenced_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    active = False
    current: list[str] = []
    for line in text.splitlines():
        if line.startswith("```"):
            if active:
                blocks.append("\n".join(current))
                current = []
            active = not active
        elif active:
            current.append(line)
    if active:
        raise ValueError("unterminated fenced code block")
    return blocks


def main() -> int:
    manifest = json.loads(MANIFEST.read_text())
    errors: list[str] = []
    if manifest.get("schema_version") != 1:
        errors.append("manifest schema_version must be 1")
    base_sha = manifest.get("upstream", {}).get("base_sha")
    if base_sha != "8b36d4fb2635b3c21998dcd8144439c9e5ba7302":
        errors.append("manifest upstream base_sha is not the verified dispatch-time SHA")

    entries = manifest.get("skills", [])
    if not entries:
        errors.append("manifest has no skills")
    seen: set[str] = set()
    for entry in entries:
        slug = entry.get("slug", "")
        path = ROOT / entry.get("distribution_path", "")
        if slug in seen:
            errors.append(f"duplicate manifest slug: {slug}")
        seen.add(slug)
        if path != ROOT / "skills" / slug / "SKILL.md":
            errors.append(f"{slug}: distribution_path must be skills/<slug>/SKILL.md")
        if not path.is_file():
            errors.append(f"{slug}: missing distributed SKILL.md")
            continue
        source = entry.get("source", {})
        if entry.get("adaptation", {}).get("policy") == "upstream-flat-copy":
            source_path = ROOT / source.get("path", "")
            if not source_path.is_file():
                errors.append(f"{slug}: missing mapped upstream source {source.get('path')}")
            elif path.read_bytes() != source_path.read_bytes():
                errors.append(f"{slug}: flat copy differs from mapped upstream source")
        try:
            metadata = frontmatter(path.read_text())
            if metadata["name"] != slug:
                errors.append(f"{slug}: frontmatter name is {metadata['name']!r}")
            blocks = fenced_blocks(path.read_text())
        except (OSError, ValueError) as exc:
            errors.append(f"{slug}: {exc}")
            continue
        for block in blocks:
            if RETIRED.search(block):
                errors.append(f"{slug}: retired durable API in executable code block")
        if entry.get("adaptation", {}).get("policy") == "hermes-kanban-adaptation":
            missing = [token for token in REQUIRED_ORCHESTRATION if token not in path.read_text()]
            if missing:
                errors.append(f"{slug}: missing current durable semantics: {', '.join(missing)}")
        for key in ("source", "upstream_base_sha", "adaptation", "version", "validation"):
            if key not in entry:
                errors.append(f"{slug}: manifest missing {key}")

    fixture_dir = ROOT / "evals" / "fixtures"
    for fixture in ("kanban-enabled.json", "kanban-disabled.json"):
        if not (fixture_dir / fixture).is_file():
            errors.append(f"missing eval fixture {fixture}")
    if not (ROOT / "LICENSE").is_file():
        errors.append("upstream MIT LICENSE is missing")

    if errors:
        print("FAIL")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(f"PASS: {len(entries)} distributed skills validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
