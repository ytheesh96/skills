#!/usr/bin/env python3
"""Synchronize unchanged upstream skills into the flat Hermes tap layout.

The command is intentionally fail-closed: it plans every mapped source change
before writing anything, and refuses to overwrite an adapted distribution when
its upstream source or support files changed.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType


DEFAULT_ROOT = Path(__file__).resolve().parents[1]


def _validator_module() -> ModuleType:
    path = Path(__file__).with_name("validate-hermes-tap.py")
    spec = importlib.util.spec_from_file_location("validate_hermes_tap", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load validator: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def changed_paths(root: Path, base_sha: str, new_sha: str) -> set[str]:
    output = git(root, "diff", "--name-only", "--find-renames", f"{base_sha}..{new_sha}")
    return {line.strip() for line in output.splitlines() if line.strip()}


def _source_paths(root: Path, entry: dict, validator: ModuleType) -> tuple[set[str], list[str]]:
    source_path = entry.get("source", {}).get("path")
    if not isinstance(source_path, str):
        return set(), [f"{entry.get('slug', '<unknown>')}: source.path is required"]
    source_file, source_error = validator.safe_relative_path(root, source_path)
    paths = {Path(source_path).as_posix()}
    if source_error or source_file is None:
        return paths, [f"{entry['slug']}: invalid mapped source: {source_error or source_path}"]
    if not source_file.is_file():
        return paths, [f"{entry['slug']}: mapped source is missing: {source_path}"]
    refs, ref_errors = validator.referenced_support_paths(
        source_file.read_text(encoding="utf-8")
    )
    errors = [f"{entry['slug']}: {message}" for message in ref_errors]
    source_dir = source_file.parent
    for ref in refs:
        support, support_error = validator.safe_relative_path(source_dir, ref)
        if support_error or support is None:
            errors.append(
                f"{entry['slug']}: invalid mapped upstream support path {ref}: "
                f"{support_error or 'empty path'}"
            )
            continue
        try:
            relative_support = support.relative_to(root.resolve())
        except ValueError:
            errors.append(f"{entry['slug']}: mapped upstream support escapes checkout: {ref}")
            continue
        paths.add(relative_support.as_posix())
        if not support.is_file():
            errors.append(f"{entry['slug']}: mapped upstream support is missing: {ref}")
    return paths, errors


def _safe_support_refs(
    directory: Path,
    refs: set[str],
    slug: str,
    validator: ModuleType,
    require_files: bool,
) -> tuple[set[str], list[str]]:
    """Normalize support references and reject traversal before any write."""

    safe_refs: set[str] = set()
    errors: list[str] = []
    for ref in refs:
        path, path_error = validator.safe_relative_path(directory, ref)
        if path_error or path is None:
            errors.append(
                f"{slug}: invalid support path {ref}: {path_error or 'empty path'}"
            )
            continue
        if require_files and not path.is_file():
            errors.append(f"{slug}: mapped upstream support is missing: {ref}")
            continue
        safe_refs.add(path.relative_to(directory.resolve()).as_posix())
    return safe_refs, errors


def plan_sync(
    root: Path, manifest: dict, changed: set[str]
) -> tuple[list[dict], list[str]]:
    """Return pure-copy actions and adapted-change errors without writing."""

    validator = _validator_module()
    actions: list[dict] = []
    errors: list[str] = []
    normalized_changed = {Path(path).as_posix() for path in changed}
    for entry in manifest.get("skills", []):
        source = entry.get("source", {})
        if source.get("kind") != "upstream":
            continue
        mapped, source_errors = _source_paths(root, entry, validator)
        if not mapped.intersection(normalized_changed):
            continue
        errors.extend(source_errors)
        policy = entry.get("adaptation", {}).get("policy")
        if policy != "upstream-flat-copy":
            overlap = sorted(mapped.intersection(normalized_changed))
            errors.append(
                f"{entry['slug']}: upstream source drift requires a reviewed adaptation update "
                f"({', '.join(overlap)})"
            )
            continue
        if source_errors:
            continue
        distribution, distribution_error = validator.safe_relative_path(
            root, entry.get("distribution_path", "")
        )
        source_file, source_error = validator.safe_relative_path(root, source["path"])
        if distribution_error or distribution is None:
            errors.append(
                f"{entry['slug']}: invalid distribution path: "
                f"{distribution_error or 'empty path'}"
            )
            continue
        if source_error or source_file is None:
            errors.append(
                f"{entry['slug']}: invalid source path: {source_error or 'empty path'}"
            )
            continue
        if not distribution.is_file():
            errors.append(f"{entry['slug']}: flat distribution is missing: {entry['distribution_path']}")
            continue
        old_refs, old_ref_errors = validator.referenced_support_paths(
            distribution.read_text(encoding="utf-8")
        )
        errors.extend(f"{entry['slug']}: {message}" for message in old_ref_errors)
        new_refs, new_ref_errors = validator.referenced_support_paths(
            source_file.read_text(encoding="utf-8")
        )
        errors.extend(f"{entry['slug']}: {message}" for message in new_ref_errors)
        old_refs, old_path_errors = _safe_support_refs(
            distribution.parent, old_refs, entry["slug"], validator, require_files=False
        )
        new_refs, new_path_errors = _safe_support_refs(
            source_file.parent, new_refs, entry["slug"], validator, require_files=True
        )
        errors.extend(old_path_errors)
        errors.extend(new_path_errors)
        if old_ref_errors or new_ref_errors or old_path_errors or new_path_errors:
            continue
        actions.append(
            {
                "entry": entry,
                "distribution": distribution,
                "source": source_file,
                "old_refs": old_refs,
                "new_refs": new_refs,
            }
        )
    return actions, errors


def apply_actions(actions: list[dict]) -> None:
    for action in actions:
        distribution = action["distribution"]
        source = action["source"]
        distribution.write_bytes(source.read_bytes())
        source_dir = source.parent
        distribution_dir = distribution.parent
        for ref in sorted(action["new_refs"]):
            source_support = source_dir / ref
            destination = distribution_dir / ref
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source_support.read_bytes())
        for ref in sorted(action["old_refs"] - action["new_refs"]):
            destination = distribution_dir / ref
            if destination.is_file():
                destination.unlink()


def sync(root: Path, upstream_ref: str = "upstream/main") -> int:
    root = root.resolve()
    manifest_path = root / "hermes-skill-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    current_base = manifest["upstream"]["base_sha"]
    new_base = git(root, "rev-parse", upstream_ref)
    if current_base == new_base:
        print(f"No upstream advance: {current_base}")
        return 0

    changed = changed_paths(root, current_base, new_base)
    actions, errors = plan_sync(root, manifest, changed)
    if errors:
        print("Refusing upstream sync:")
        for error in errors:
            print(f"- {error}")
        return 1

    apply_actions(actions)
    manifest["upstream"]["base_sha"] = new_base
    # This cursor is deliberately separate from each source.base_sha: source
    # lineage remains immutable while the repository-wide sync cursor advances.
    for entry in manifest.get("skills", []):
        entry["upstream_base_sha"] = new_base
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        f"Synchronized upstream {current_base} -> {new_base}; "
        f"updated {len(actions)} pure-copy skill(s)"
    )
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--upstream-ref", default="upstream/main")
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args()
    try:
        sys.exit(sync(args.root, args.upstream_ref))
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        print(f"upstream sync command failed: {detail}", file=sys.stderr)
        sys.exit(exc.returncode or 1)
