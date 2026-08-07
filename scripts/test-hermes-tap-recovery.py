#!/usr/bin/env python3
"""Focused regression oracle for the recovery-script-presence check (d).

Red-green proof:
- Green: the checked-in tree (and a faithful copy of it) must PASS the
  recovery-script-presence check declared by docs/cron.md.
- Red:   removing one script that docs/cron.md declares must make the
  check FAIL, proving it actually guards against a missing file.
"""
from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[1]


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def copy_candidate(destination: Path) -> None:
    shutil.copytree(
        ROOT,
        destination,
        ignore=shutil.ignore_patterns(
            ".git", ".hermes-tap-smoke*", "node_modules", "__pycache__"
        ),
    )


def main() -> int:
    validator = load_module(ROOT / "scripts/validate-hermes-tap.py", "validate_hermes_tap")

    # Green: the checked-in tree must satisfy the recovery-script check.
    real_errors = validator.validate(ROOT)
    if any("docs/cron.md declares" in error for error in real_errors):
        raise AssertionError(
            "checked-in tree fails the recovery-script-presence check (d):\n- "
            + "\n- ".join(real_errors)
        )

    # Red: a faithful copy with one declared script deleted must FAIL (d).
    with tempfile.TemporaryDirectory(prefix="hermes-tap-recovery-") as directory:
        candidate = Path(directory) / "candidate"
        copy_candidate(candidate)

        missing = candidate / "scripts/recovery/kanban_stall_watch.py"
        if not missing.is_file():
            raise AssertionError("setup failed: kanban_stall_watch.py not present to delete")
        missing.unlink()

        candidate_errors = validator.validate(candidate)
        marker = "docs/cron.md declares scripts/recovery/kanban_stall_watch.py but it does not exist"
        if not any(marker in error for error in candidate_errors):
            raise AssertionError(
                "recovery-script-presence check (d) did NOT fail closed on a missing file:\n- "
                + "\n- ".join(candidate_errors)
            )

    print("PASS: recovery-script-presence regression oracle")
    print("- checked-in tree satisfies check (d) on the real tree")
    print("- deleting a docs/cron.md-declared script fails check (d) (red-green proof)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
