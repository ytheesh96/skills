#!/usr/bin/env python3
"""Run deterministic regression checks for the Hermes tap manifest contract."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
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


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def copy_candidate(destination: Path) -> None:
    shutil.copytree(
        ROOT,
        destination,
        ignore=shutil.ignore_patterns(
            ".git", ".hermes-tap-smoke*", "node_modules", "__pycache__"
        ),
    )


def run_sync(checkout: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/sync-upstream-flat.py"),
            "--root",
            str(checkout),
            "--upstream-ref",
            "HEAD",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def main() -> int:
    validator = load_module(ROOT / "scripts/validate-hermes-tap.py", "validate_hermes_tap")
    synchronizer = load_module(ROOT / "scripts/sync-upstream-flat.py", "sync_upstream_flat")

    current_errors = validator.validate(ROOT)
    if current_errors:
        raise AssertionError(
            "the checked-in candidate must validate before regression setup:\n- "
            + "\n- ".join(current_errors)
        )

    # A cursor advance is valid when the manifest's current cursor and every
    # entry cursor agree. The original import SHA is an immutable lineage
    # anchor, not a hard-coded validator allowlist.
    advanced_base = "1" * 40
    with tempfile.TemporaryDirectory(prefix="hermes-tap-regression-") as directory:
        candidate = Path(directory) / "candidate"
        copy_candidate(candidate)
        manifest_path = candidate / "hermes-skill-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        initial_base = manifest["upstream"]["initial_base_sha"]
        manifest["upstream"]["base_sha"] = advanced_base
        for entry in manifest["skills"]:
            entry["upstream_base_sha"] = advanced_base
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        advanced_errors = validator.validate(candidate)
        if advanced_errors:
            raise AssertionError(
                "a valid upstream cursor advance must validate:\n- "
                + "\n- ".join(advanced_errors)
            )
        if json.loads(manifest_path.read_text(encoding="utf-8"))["upstream"]["initial_base_sha"] != initial_base:
            raise AssertionError("cursor advance rewrote the immutable initial upstream base")

        broken_support = Path(directory) / "broken-support"
        copy_candidate(broken_support)
        missing_support = broken_support / "skills/writing-plans/references/UPSTREAM_LICENSE.md"
        missing_support.unlink()
        missing_errors = validator.validate(broken_support)
        if not any("missing support file references/UPSTREAM_LICENSE.md" in error for error in missing_errors):
            raise AssertionError("support-path validation did not fail closed on a missing file")

        adapted = next(
            entry for entry in manifest["skills"] if entry["adaptation"]["policy"] != "upstream-flat-copy"
        )
        adapted_path = candidate / adapted["distribution_path"]
        adapted_path.write_text(
            adapted_path.read_text(encoding="utf-8") + "\n# intentional drift\n",
            encoding="utf-8",
        )
        drift_errors = validator.validate(candidate)
        if not any("distribution_sha256" in error for error in drift_errors):
            raise AssertionError("adapted distribution drift did not fail the immutable content gate")

        fresh_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        adapted_source = next(
            entry for entry in fresh_manifest["skills"] if entry["slug"] == "wayfinder"
        )["source"]["path"]
        actions, sync_errors = synchronizer.plan_sync(
            candidate, fresh_manifest, {adapted_source}
        )
        if actions or not any("reviewed adaptation update" in error for error in sync_errors):
            raise AssertionError("upstream drift for an adapted source was not rejected before writes")

        pure_entry = next(
            entry for entry in fresh_manifest["skills"] if entry["slug"] == "writing-shape"
        )
        actions, sync_errors = synchronizer.plan_sync(
            candidate, fresh_manifest, {pure_entry["source"]["path"]}
        )
        if sync_errors or not any(action["entry"]["slug"] == "writing-shape" for action in actions):
            raise AssertionError("upstream drift for a pure copy was not planned for synchronization")

    # Exercise the real synchronizer on a synthetic upstream advance. A pure
    # copy is refreshed and the current cursor advances; validation then proves
    # the resulting candidate is coherent.
    with tempfile.TemporaryDirectory(prefix="hermes-tap-sync-advance-") as directory:
        sync_checkout = Path(directory) / "candidate"
        copy_candidate(sync_checkout)
        git(sync_checkout, "init", "-q")
        git(sync_checkout, "config", "user.name", "Hermes tap regression")
        git(sync_checkout, "config", "user.email", "regression@example.invalid")
        git(sync_checkout, "add", ".")
        git(sync_checkout, "commit", "-qm", "base")
        base_sha = git(sync_checkout, "rev-parse", "HEAD")

        sync_manifest_path = sync_checkout / "hermes-skill-manifest.json"
        sync_manifest = json.loads(sync_manifest_path.read_text(encoding="utf-8"))
        immutable_source_bases = {
            entry["slug"]: entry["source"]["base_sha"] for entry in sync_manifest["skills"]
        }
        sync_manifest["upstream"]["base_sha"] = base_sha
        for entry in sync_manifest["skills"]:
            entry["upstream_base_sha"] = base_sha
        sync_manifest_path.write_text(
            json.dumps(sync_manifest, indent=2) + "\n", encoding="utf-8"
        )
        git(sync_checkout, "add", "hermes-skill-manifest.json")
        git(sync_checkout, "commit", "-qm", "record current upstream cursor")

        pure_source = sync_checkout / "skills/in-progress/writing-shape/SKILL.md"
        pure_source.write_text(
            pure_source.read_text(encoding="utf-8") + "\n<!-- simulated upstream advance -->\n",
            encoding="utf-8",
        )
        git(sync_checkout, "add", str(pure_source.relative_to(sync_checkout)))
        git(sync_checkout, "commit", "-qm", "simulate pure-copy upstream advance")
        new_base = git(sync_checkout, "rev-parse", "HEAD")

        result = run_sync(sync_checkout)
        if result.returncode != 0:
            raise AssertionError("real synchronizer rejected a pure-copy advance:\n" + result.stdout)
        synced_manifest = json.loads(sync_manifest_path.read_text(encoding="utf-8"))
        if synced_manifest["upstream"]["base_sha"] != new_base:
            raise AssertionError("real synchronizer did not advance manifest upstream.base_sha")
        if any(entry["upstream_base_sha"] != new_base for entry in synced_manifest["skills"]):
            raise AssertionError("real synchronizer left an entry upstream cursor behind")
        if {
            entry["slug"]: entry["source"]["base_sha"] for entry in synced_manifest["skills"]
        } != immutable_source_bases:
            raise AssertionError("real synchronizer rewrote immutable source lineage anchors")
        direct_copy = sync_checkout / "skills/writing-shape/SKILL.md"
        if direct_copy.read_bytes() != pure_source.read_bytes():
            raise AssertionError("real synchronizer did not refresh the pure-copy distribution")
        synced_errors = validator.validate(sync_checkout)
        if synced_errors:
            raise AssertionError(
                "candidate after a pure-copy upstream advance does not validate:\n- "
                + "\n- ".join(synced_errors)
            )

    # The real synchronizer must reject adapted drift before touching either the
    # manifest or any distribution file.
    with tempfile.TemporaryDirectory(prefix="hermes-tap-sync-") as directory:
        sync_checkout = Path(directory) / "candidate"
        copy_candidate(sync_checkout)
        git(sync_checkout, "init", "-q")
        git(sync_checkout, "config", "user.name", "Hermes tap regression")
        git(sync_checkout, "config", "user.email", "regression@example.invalid")
        git(sync_checkout, "add", ".")
        git(sync_checkout, "commit", "-qm", "base")
        base_sha = git(sync_checkout, "rev-parse", "HEAD")

        sync_manifest_path = sync_checkout / "hermes-skill-manifest.json"
        sync_manifest = json.loads(sync_manifest_path.read_text(encoding="utf-8"))
        sync_manifest["upstream"]["base_sha"] = base_sha
        for entry in sync_manifest["skills"]:
            entry["upstream_base_sha"] = base_sha
        sync_manifest_path.write_text(
            json.dumps(sync_manifest, indent=2) + "\n", encoding="utf-8"
        )
        adapted_source = sync_checkout / "skills/engineering/wayfinder/SKILL.md"
        adapted_source.write_text(
            adapted_source.read_text(encoding="utf-8") + "\n# simulated upstream change\n",
            encoding="utf-8",
        )
        git(sync_checkout, "add", ".")
        git(sync_checkout, "commit", "-qm", "simulate upstream adaptation drift")
        before_manifest = sync_manifest_path.read_bytes()
        before_distribution = (sync_checkout / "skills/wayfinder/SKILL.md").read_bytes()
        result = run_sync(sync_checkout)
        if result.returncode == 0 or "reviewed adaptation update" not in result.stdout:
            raise AssertionError(
                "real synchronizer did not fail closed on adapted drift:\n" + result.stdout
            )
        if sync_manifest_path.read_bytes() != before_manifest:
            raise AssertionError("synchronizer changed the manifest after rejecting adapted drift")
        if (sync_checkout / "skills/wayfinder/SKILL.md").read_bytes() != before_distribution:
            raise AssertionError("synchronizer overwrote an adapted distribution before review")

    # The validator must fail closed when a committed script hard-codes an
    # absolute ~/.hermes path instead of resolving it from HERMES_HOME or
    # Path.home(). A temporary fixture under scripts/ exercises the gate; the
    # real tree then validates again once the fixture is removed, proving the
    # check is precise and does not false-positive on the shipped scripts.
    # The defective literal is assembled by concatenation so THIS test source
    # does not itself contain a hard-coded absolute .hermes path (that would
    # trip the very gate under test); only the generated fixture does.
    bad_path = "/Users/yt/.her" + "mes/state/foreground-notify-target.json"
    fixture = ROOT / "scripts" / "_regression_bad_fixture.py"
    fixture.write_text(f"HERMES_HOME = {bad_path!r}\n", encoding="utf-8")
    try:
        injected_errors = validator.validate(ROOT)
        if not any("hard-coded absolute .hermes path" in error for error in injected_errors):
            raise AssertionError(
                "validator did not flag a hard-coded absolute .hermes path:\\n- "
                + "\n- ".join(injected_errors)
            )
        if not any(str(fixture.relative_to(ROOT)) in error for error in injected_errors):
            raise AssertionError(
                "hard-coded-path error did not name the offending fixture:\\n- "
                + "\n- ".join(injected_errors)
            )
    finally:
        fixture.unlink()

    # The person-specific-leak guard (check c) must fail closed when a skill's
    # distribution package contains a maintainer leak: a GitHub personal-access
    # token (ghp_), "second-brain" personal branding, or a private home path.
    # The fixture is dropped inside an existing skill's distribution package so
    # it is scanned by the portability checker, then removed so the real tree
    # still validates (RED injected, GREEN recovered).
    leak_package = ROOT / "skills" / "kanban-worker"
    leak_fixture = leak_package / "_regression_leak_fixture.md"
    leak_fixture.write_text(
        "# leak fixture\n"
        "token ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890 must never ship.\n"
        "This is my second-brain knowledge setup.\n"
        "Home is /Users/yt/.hermes/state/leak.json.\n",
        encoding="utf-8",
    )
    try:
        leak_errors = validator.validate(ROOT)
        if not any("public-portability violation" in error for error in leak_errors):
            raise AssertionError(
                "validator did not flag a person-specific leak in a skill package:\n- "
                + "\n- ".join(leak_errors)
            )
        if not any(str(leak_fixture.relative_to(ROOT)) in error for error in leak_errors):
            raise AssertionError(
                "leak error did not name the offending fixture:\n- "
                + "\n- ".join(leak_errors)
            )
    finally:
        leak_fixture.unlink()

    clean_errors = validator.validate(ROOT)
    if clean_errors:
        raise AssertionError(
            "tree must validate again after the bad fixture is removed:\\n- "
            + "\n- ".join(clean_errors)
        )

    print("PASS: Hermes tap regression oracle")
    print("- current manifest/provenance validates with 0 missing support paths")
    print("- advanced upstream cursor validates without a historical SHA allowlist")
    print("- missing distributed support files fail the path-completeness gate")
    print("- adapted distribution content drift fails the immutable hash gate")
    print("- adapted upstream source drift is rejected before any write")
    print("- pure-copy upstream drift is planned and applied by the real synchronizer")
    print("- synchronized candidate validates with the advanced cursor")
    print("- person-specific-leak guard fails closed on ghp_/second-brain/private-path fixture")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
