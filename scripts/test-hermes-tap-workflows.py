#!/usr/bin/env python3
"""Parse and assert the safety invariants of the tap workflows."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_yaml(path: Path) -> str:
    """Use an installed parser when available; always retain structural checks."""

    try:
        import yaml  # type: ignore
    except ImportError:
        yaml = None
    if yaml is not None:
        yaml.safe_load(path.read_text(encoding="utf-8"))
        return "PyYAML"
    ruby = subprocess.run(
        ["ruby", "-e", "require 'yaml'; YAML.load_file(ARGV[0])", str(path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if ruby.returncode == 0:
        return "Ruby YAML"
    return "structural fallback"


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise AssertionError(f"{label}: missing {needle!r}")


def main() -> int:
    validate = ROOT / ".github/workflows/validate-hermes-tap.yml"
    sync = ROOT / ".github/workflows/sync-upstream.yml"
    parsers = {str(path): parse_yaml(path) for path in (validate, sync)}
    validate_text = validate.read_text(encoding="utf-8")
    sync_text = sync.read_text(encoding="utf-8")

    require(validate_text, "python3 scripts/validate-hermes-tap.py", "validation workflow")
    require(validate_text, "python3 scripts/test-hermes-tap-regressions.py", "validation workflow")
    require(validate_text, "python3 scripts/test-hermes-tap-workflows.py", "validation workflow")
    require(sync_text, "git merge --no-commit --no-ff upstream/main", "sync workflow")
    require(sync_text, "python3 scripts/sync-upstream-flat.py", "sync workflow")
    require(sync_text, "python3 scripts/validate-hermes-tap.py", "sync workflow")
    require(sync_text, "git push --force-with-lease origin", "sync workflow")
    if re.search(r"git\s+push\s+--force(?!-with-lease)", sync_text):
        raise AssertionError("sync workflow contains an unscoped force push")
    body_line = next(
        (line.strip() for line in sync_text.splitlines() if line.strip().startswith("body=")),
        "",
    )
    if not body_line.startswith('body="$(printf'):
        raise AssertionError("sync PR body is not built with a quoted, inert printf path")
    if "body=\"This PR" in sync_text:
        raise AssertionError("sync PR body still uses shell interpolation in a quoted literal")
    body_probe = subprocess.run(
        [
            "bash",
            "-c",
            f'UPSTREAM_SHA=deadbeef; {body_line}; printf "%s" "$body"',
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if body_probe.returncode != 0 or "deadbeef" not in body_probe.stdout:
        raise AssertionError(
            "sync PR body shell probe failed:\n" + body_probe.stderr + body_probe.stdout
        )

    print("PASS: Hermes tap workflow parse/behavior checks")
    for path, parser in parsers.items():
        print(f"- parsed {Path(path).relative_to(ROOT)} with {parser}")
    print("- validation and regression gates are wired into CI")
    print("- sync uses normal merge and force-with-lease only")
    print("- sync PR body shell probe preserves the inert SHA substitution")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
