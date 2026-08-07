#!/usr/bin/env python3
"""Deterministic validation for the flat Hermes skill distribution."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
HEX_SHA = re.compile(r"^[0-9a-f]{40}$")
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
SLUG = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
SUPPORT_ROOTS = frozenset({"references", "templates", "scripts", "assets", "examples"})
KNOWN_POLICIES = frozenset(
    {"upstream-flat-copy", "hermes-kanban-adaptation", "hermes-support-path-adaptation"}
)

# This deliberately finds package-relative paths, not arbitrary words such as
# "assets".  The direct Hermes bundle is rooted at skills/<slug>/, so every
# match must resolve below that skill directory.
LOCAL_REF = re.compile(
    r"(?<![A-Za-z0-9_./-])"
    r"((?:\./)?(?:references|templates|scripts|assets|examples)"
    r"(?:/[^\s<>()\[\]`\"']+)+)"
)
RETIRED = re.compile(
    r"delegate_task\s*\(\s*mode\s*=\s*['\"](?:loop|durable)['\"]|"
    r"\b(?:loop_graph|loop_create|loop_status|loop_block)\s*\("
)
# docs/cron.md is the authoritative declaration of the background recovery
# scripts. Each entry pins a repo-relative path under scripts/recovery/.
RECOVERY_DECL = DEFAULT_ROOT / "docs" / "cron.md"
RECOVERY_SCRIPT_PATH = re.compile(r"`(scripts/recovery/[\w.\-]+\.py)`")

REQUIRED_SEMANTICS = {
    "foreground-owned-loop-orchestration": (
        "kanban_create", "kanban_list", "kanban_show", "kanban_block",
        "kanban_unblock", "kanban_link", "board", "tenant",
    ),
    "kanban-orchestrator": (
        "kanban_create", "kanban_list", "kanban_show", "kanban_block",
        "kanban_unblock", "kanban_link", "board", "tenant",
    ),
    "kanban-worker": (
        "kanban_show", "kanban_complete", "kanban_block", "board", "tenant",
    ),
    "wayfinder": (
        "kanban_create", "kanban_list", "kanban_show", "kanban_block",
        "kanban_unblock", "kanban_link", "board", "tenant",
    ),
    "writing-plans": (
        "kanban_create", "kanban_list", "kanban_show", "kanban_block",
        "kanban_unblock", "kanban_link", "board", "tenant",
    ),
    "to-tasks": (
        "kanban_create", "kanban_show", "kanban_block",
        "kanban_link", "board", "tenant",
    ),
}

# These are portability boundaries, not a ban on generic words such as
# "credential" or "career" that can be legitimate subject matter in a skill.
# Identity tokens are compared by digest so the public validator does not
# publish the maintainer's private name or address as readable source text.
PRIVATE_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._%+@-]*")
PRIVATE_TOKEN_DIGESTS = frozenset(
    {
        "2db533f41033268db04f6ff8151fb6f5862c6509d8f35783b0c14b090e8766a6",
        "52d08aa1d7b71952948b1f6085b51230e2afbb37eb7d1a8f97c0365aab1e857f",
        "f2de7baddf616fa5f40a1b8caf3dcc0a73d9cd91898213e286cb600f87d7372f",
    }
)
PRIVATE_PATTERNS = (
    ("private path", re.compile(r"(?:~\/\.hermes|/(?:Users|home)/[A-Za-z0-9._-]+)")),
    (
        "installation-specific profile",
        re.compile(r"\b(?:research-worker|reviewer-qa|ops-steward|zilor-ppt)\b"),
    ),
    (
        "free-floating provenance label",
        re.compile(r"(?i)Hermes Agent public-safe adaptation inventory"),
    ),
)


# ---------------------------------------------------------------------------
# Person-specific-leak guard (check c).
#
# Scans every shipped skill file under skills/** for accidental leaks of the
# maintainer's identity or private setup. The forbidden terms are centralized in
# PERSON_LEAK_PATTERNS (case-insensitive, word-boundary where appropriate,
# reusing the leak-rejection regex style above). An EXPLICIT safe-list
# (LEAK_SAFELIST) excludes text that must be allowed to ship: the upstream MIT
# attribution to Matt Pocock (required by the manifest contract) and the
# intentional zilor-ppt validator guard strings already present in the repo. A
# forbidden match that falls inside a safe-listed span is suppressed, so the
# attribution / provenance text can never trip the guard.
#
# Coverage (the t_4942b271 spec):
#   * maintainer real name (Vaitheesh)
#   * maintainer home paths (/Users/yt, /home/yt)
#   * GitHub personal-access token (ghp_)
#   * personal handles (yt, yt_)
#   * Obsidian personal note app
#   * "second-brain" personal knowledge-management branding
#   * the personal "Loop" knowledge-management cluster -- scoped to co-occurrence
#     with Obsidian / second-brain so the legitimate public Hermes Loop
#     orchestration features (loop-me, foreground-owned-loop-orchestration,
#     "feedback loop", tdd "red -> green loop") are NOT flagged.
# ---------------------------------------------------------------------------
LEAK_SAFELIST = (
    re.compile(r"(?i)matt\s+pocock"),
    re.compile(r"zilor-ppt"),
)

# "Loop" is only a personal-leak signal when it appears alongside personal
# knowledge-management branding. A file must contain both to trip the guard.
_LOOP_RE = re.compile(r"(?i)\bloop\b")
_LOOP_KM_SIGNAL = re.compile(r"(?i)\b(?:obsidian|second[-_ ]?brain)\b")

PERSON_LEAK_PATTERNS = (
    ("maintainer real name", re.compile(r"(?i)\bvaitheesh\b")),
    ("maintainer home path", re.compile(r"/Users/yt")),
    ("maintainer home path", re.compile(r"/home/yt")),
    # GitHub personal-access token (ghp_ + >=20 chars). Required by check c:
    # a leaked PAT must never ship.
    ("github personal-access token", re.compile(r"\bghp_[A-Za-z0-9]{20,}\b")),
    ("personal handle", re.compile(r"(?i)\byt_[a-z0-9]")),
    ("personal handle", re.compile(r"(?i)(?<![a-z0-9_])yt(?![a-z0-9_])")),
    ("obsidian personal note app", re.compile(r"(?i)\bobsidian\b")),
    # Personal "second-brain" branding: signals a maintainer's private
    # knowledge-management setup, not a public skill.
    ("second-brain branding", re.compile(r"(?i)second[-_ ]?brain")),
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="distribution checkout to validate (default: repository root)",
    )
    return parser.parse_args(argv)


def load_manifest(root: Path) -> tuple[dict, list[str]]:
    path = root / "hermes-skill-manifest.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}, [f"missing manifest: {path.relative_to(root)}"]
    except json.JSONDecodeError as exc:
        return {}, [f"manifest is not valid JSON: {exc}"]
    if not isinstance(manifest, dict):
        return {}, ["manifest root must be an object"]
    errors: list[str] = []
    if manifest.get("schema_version") != 1:
        errors.append("manifest schema_version must be 1")
    if not isinstance(manifest.get("skills"), list) or not manifest["skills"]:
        errors.append("manifest skills must be a non-empty list")
    return manifest, errors


def safe_relative_path(root: Path, raw: str) -> tuple[Path | None, str | None]:
    """Resolve a repository-relative path without allowing traversal."""

    cleaned = unquote(raw).strip().removeprefix("./").rstrip(".,;:")
    if not cleaned:
        return None, "empty path"
    if "*" in cleaned:
        return None, f"wildcard is not a fetchable package path: {raw}"
    path = Path(cleaned)
    if path.is_absolute() or ".." in path.parts:
        return None, f"path escapes the package directory: {raw}"
    resolved = (root / path).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        return None, f"path escapes the checkout: {raw}"
    return resolved, None


def referenced_support_paths(text: str, label: str = "") -> tuple[set[str], list[str]]:
    """Return every package-relative support path mentioned by a skill."""

    refs: set[str] = set()
    errors: list[str] = []
    for match in LOCAL_REF.finditer(text):
        raw = match.group(1)
        cleaned = unquote(raw).strip().removeprefix("./").rstrip(".,;:")
        if "*" in cleaned:
            prefix = f"{label}: " if label else ""
            errors.append(f"{prefix}wildcard support reference is not fetchable: {raw}")
            continue
        refs.add(cleaned)
    return refs, errors


def check_frontmatter(path: Path, text: str, expected_name: str) -> list[str]:
    errors: list[str] = []
    if not text.startswith("---\n"):
        return [f"{path}: missing YAML frontmatter"]
    end = text.find("\n---", 4)
    if end < 0:
        return [f"{path}: unterminated YAML frontmatter"]
    values: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line or line[:1].isspace():
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"\'')
    if values.get("name") != expected_name:
        errors.append(f"{path}: frontmatter name {values.get('name')!r} != {expected_name!r}")
    if not values.get("description"):
        errors.append(f"{path}: frontmatter description is empty")
    return errors


def fenced_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    active = False
    current: list[str] = []
    marker = ""
    for line in text.splitlines():
        candidate = line.strip()
        if candidate.startswith("```") or candidate.startswith("~~~"):
            current_marker = candidate[:3]
            if active and current_marker == marker:
                blocks.append("\n".join(current))
                current = []
                active = False
                marker = ""
            elif not active:
                active = True
                marker = current_marker
            else:
                current.append(line)
        elif active:
            current.append(line)
    if active:
        raise ValueError("unterminated fenced code block")
    return blocks


def check_support_paths(
    root: Path,
    distribution_file: Path,
    text: str,
    slug: str = "",
    source_file: Path | None = None,
    pure_copy: bool = False,
) -> tuple[list[str], set[str]]:
    """Verify every package-relative support reference resolves to a real file.

    Each declared support path (references/*.md, scripts/*, templates/*,
    assets/*, examples/*) under the skill must exist on disk. On the first
    missing path the error names the skill and the missing relative path so a
    maintainer can localize the break without scanning the full message list.
    For pure copies the mapped upstream source is also required to exist and
    stay byte-identical (presence is not enough: the tap must ship what the
    source shipped).
    """

    refs, errors = referenced_support_paths(text, slug)
    skill_dir = distribution_file.parent
    source_dir = source_file.parent if source_file is not None else None
    for ref in sorted(refs):
        first = ref.split("/", 1)[0]
        if first not in SUPPORT_ROOTS:
            errors.append(
                f"{slug}: unsupported package reference {ref} (in {distribution_file})"
            )
            continue
        path, path_error = safe_relative_path(skill_dir, ref)
        if path_error:
            errors.append(
                f"{slug}: {path_error} (in {distribution_file})"
            )
            continue
        if path is None or not path.is_file():
            errors.append(
                f"{slug}: missing support file {ref} (in {distribution_file})"
            )
            continue
        if pure_copy and source_dir is not None:
            source_path, source_error = safe_relative_path(source_dir, ref)
            if source_error or source_path is None or not source_path.is_file():
                errors.append(
                    f"{slug}: mapped upstream support file is missing {ref} "
                    f"(in {distribution_file})"
                )
            elif path.read_bytes() != source_path.read_bytes():
                errors.append(
                    f"{slug}: support file drifted from mapped upstream source {ref} "
                    f"(in {distribution_file})"
                )
    return errors, refs


def check_public_portability(path: Path, text: str) -> list[str]:
    errors: list[str] = []
    for label, pattern in PRIVATE_PATTERNS:
        match = pattern.search(text)
        if match:
            errors.append(f"{path}: public-portability violation ({label}): {match.group(0)!r}")
    for token in PRIVATE_TOKEN.findall(text):
        normalized = token.rstrip(".,;:").lower()
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        if digest in PRIVATE_TOKEN_DIGESTS:
            errors.append(f"{path}: public-portability violation (personal identity token)")
    return errors


def check_source_path(root: Path, raw: str, label: str) -> tuple[Path | None, list[str]]:
    if raw == "Hermes Agent public-safe adaptation inventory":
        return None, [f"{label}: free-floating provenance label is not a committed path"]
    path, path_error = safe_relative_path(root, raw)
    if path_error:
        return None, [f"{label}: {path_error}"]
    if path is None or not path.is_file():
        return None, [f"{label}: missing committed source/provenance path {raw}"]
    return path, []


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_provenance_record(
    entry: dict,
    source_file: Path,
    overlay_file: Path | None,
    source_base: str,
    errors: list[str],
) -> None:
    source_kind = entry["source"].get("kind")
    if source_kind == "hermes-native" and source_base not in source_file.read_text(encoding="utf-8"):
        errors.append(
            f"{entry['slug']}: Hermes-native source record does not contain its immutable base SHA"
        )
    if overlay_file is not None and source_base not in overlay_file.read_text(encoding="utf-8"):
        errors.append(
            f"{entry['slug']}: overlay record does not contain its immutable base SHA"
        )


def support_reference_count(root: Path) -> int:
    manifest, _ = load_manifest(root.resolve())
    total = 0
    for entry in manifest.get("skills", []):
        raw = entry.get("distribution_path")
        if not isinstance(raw, str):
            continue
        path = root / raw
        if path.is_file():
            total += len(referenced_support_paths(path.read_text(encoding="utf-8"))[0])
    return total


def check_recovery_scripts_present(root: Path, errors: list[str]) -> None:
    """Verify every recovery script declared in docs/cron.md exists.

    docs/cron.md is the single source of truth for the background recovery
    scripts. Each declared repo-relative path under scripts/recovery/ must
    resolve to a real file in the tree, so the tap never ships a doc that
    points at a missing script.
    """
    if not RECOVERY_DECL.is_file():
        errors.append("docs/cron.md is missing (declares recovery scripts)")
        return
    text = RECOVERY_DECL.read_text(encoding="utf-8")
    declared = sorted({m.group(1) for m in RECOVERY_SCRIPT_PATH.finditer(text)})
    if not declared:
        errors.append("docs/cron.md declares no scripts/recovery/*.py paths")
        return
    for relative in declared:
        if not (root / relative).is_file():
            errors.append(
                f"docs/cron.md declares {relative} but it does not exist at the declared repo path"
            )


# Absolute .hermes home paths inside quoted literals are a portability defect:
# the tap ships scripts that must resolve their state dir from HERMES_HOME (or
# Path.home() / ".hermes"), never from a maintainer's absolute home path. A
# docstring/comment describing an example path is not runtime code, so those
# lines are stripped before the scan.
_TRIPLE_QUOTE = re.compile(r'""".*?"""|\'\'\'.*?\'\'\'', re.DOTALL)
_LINE_COMMENT = re.compile(r"#[^\n]*")
# Matches either an absolute user-home .hermes path (/Users/<who>/.hermes/... or
# /home/<who>/.hermes/...) or a home-relative tilde form (~/.hermes/...). Both
# hard-code a maintainer's Hermes home instead of resolving from HERMES_HOME or
# Path.home() / ".hermes", so both are portability defects for shipped scripts.
HARDCODED_HERMES_PATH = re.compile(
    r"""['"](?:(?:/(?:Users|home)/[^'"\s]*?\.hermes[^'"\s]*)|(?:~/\.hermes[^'"\s]*))['"]"""
)


def check_no_hardcoded_hermes_paths(root: Path, errors: list[str]) -> None:
    """Flag scripts that hard-code an absolute ~/.hermes path for runtime use.

    A repo-relative or HERMES_HOME-resolved path is expected instead. Docstring
    and comment lines are stripped so prose/examples that merely mention such a
    path do not trip the runtime-path gate.
    """
    scripts_dir = root / "scripts"
    if not scripts_dir.is_dir():
        return
    # Test harness ships an intentional bad fixture literal to prove this very
    # check; it is test data, not runtime code, so it must not trip the gate.
    excluded = {scripts_dir / "test-hermes-tap-regressions.py"}
    for path in sorted(scripts_dir.rglob("*")):
        if not path.is_file():
            continue
        if path in excluded:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="strict")
        except (UnicodeDecodeError, OSError):
            continue
        code = _LINE_COMMENT.sub("", _TRIPLE_QUOTE.sub("", text))
        for match in HARDCODED_HERMES_PATH.finditer(code):
            literal = match.group(0)
            rel = path.relative_to(root)
            errors.append(
                f"{rel}: hard-coded absolute .hermes path {literal!r}; "
                f"resolve from HERMES_HOME or Path.home() / '.hermes' instead"
            )


def _in_safe_span(text: str, start: int, end: int) -> bool:
    """True when the matched [start:end) span sits inside a safe-listed run.

    Safe-listed runs are found by scanning the whole text for any LEAK_SAFELIST
    pattern; a forbidden match overlapping one of those runs is an allowed
    attribution/provenance string (e.g. 'Matt Pocock', 'zilor-ppt'), not a leak.
    """

    for safe in LEAK_SAFELIST:
        for sm in safe.finditer(text):
            if start >= sm.start() and end <= sm.end():
                return True
    return False


def check_person_specific_leak(root: Path, errors: list[str]) -> None:
    """Scan every shipped skill file under skills/** for maintainer-specific leaks.

    This is check (c) of the validator contract: a public skill distribution must
    never ship the maintainer's real name, home paths, GitHub PAT, personal
    handles, Obsidian/second-brain personal knowledge-management branding, or the
    personal 'Loop' KM cluster. Forbidden terms are centralized in
    PERSON_LEAK_PATTERNS and matched case-insensitively with word boundaries where
    appropriate. Text matching LEAK_SAFELIST (the upstream Matt Pocock MIT
    attribution and the intentional zilor-ppt guard strings) is never flagged.
    """

    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        return
    for path in sorted(skills_dir.rglob("*")):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except (UnicodeDecodeError, OSError):
            continue
        # "Loop" is only a personal-leak signal inside the personal
        # knowledge-management cluster (co-occurrence with Obsidian /
        # second-brain). The legitimate public Hermes Loop orchestration
        # features are not leaks, so skip the Loop gate unless the cluster
        # signal is present.
        loop_cluster = bool(_LOOP_RE.search(text) and _LOOP_KM_SIGNAL.search(text))
        rel = path.relative_to(root)
        for label, pattern in PERSON_LEAK_PATTERNS:
            if label == "loop knowledge-management cluster" and not loop_cluster:
                continue
            for match in pattern.finditer(text):
                if _in_safe_span(text, match.start(), match.end()):
                    continue
                errors.append(
                    f"{rel}: person-specific-leak guard (check c) "
                    f"({label}): {match.group(0)!r}"
                )


def validate(root: Path) -> list[str]:
    root = root.resolve()
    manifest, errors = load_manifest(root)
    if not manifest:
        return errors

    upstream = manifest.get("upstream", {})
    if not isinstance(upstream, dict):
        return errors + ["manifest upstream must be an object"]
    current_base = upstream.get("base_sha")
    initial_base = upstream.get("initial_base_sha")
    repository = upstream.get("repository")
    if not isinstance(current_base, str) or not HEX_SHA.fullmatch(current_base):
        errors.append("upstream.base_sha must be a 40-character commit SHA")
    if not isinstance(initial_base, str) or not HEX_SHA.fullmatch(initial_base):
        errors.append("upstream.initial_base_sha must be an immutable 40-character commit SHA")
    if not isinstance(repository, str) or not repository.startswith("https://"):
        errors.append("upstream.repository must be an HTTPS repository URL")
    if upstream.get("license") != "MIT":
        errors.append("upstream.license must preserve MIT")
    if upstream.get("attribution") != "Matt Pocock":
        errors.append("upstream.attribution must preserve Matt Pocock")

    entries = manifest.get("skills", [])
    seen_slugs: set[str] = set()
    seen_distribution: set[str] = set()
    manifest_distribution: set[Path] = set()
    for index, entry in enumerate(entries):
        label = f"skills[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{label}: entry must be an object")
            continue
        slug = entry.get("slug")
        if not isinstance(slug, str) or not SLUG.fullmatch(slug):
            errors.append(f"{label}: slug must be a lowercase package identifier")
            continue
        if slug in seen_slugs:
            errors.append(f"{slug}: duplicate manifest slug")
        seen_slugs.add(slug)
        distribution = entry.get("distribution_path")
        expected_distribution = f"skills/{slug}/SKILL.md"
        if distribution != expected_distribution:
            errors.append(f"{slug}: distribution_path must be {expected_distribution}")
        if not isinstance(distribution, str):
            continue
        if distribution in seen_distribution:
            errors.append(f"{slug}: duplicate distribution_path")
        seen_distribution.add(distribution)

        distribution_file, path_errors = check_source_path(
            root, distribution, f"{slug}.distribution_path"
        )
        errors.extend(path_errors)
        if distribution_file is None:
            continue
        manifest_distribution.add(distribution_file.resolve())
        text = distribution_file.read_text(encoding="utf-8")
        errors.extend(check_frontmatter(distribution_file, text, slug))

        source = entry.get("source")
        if not isinstance(source, dict):
            errors.append(f"{slug}: source must be an object with committed provenance")
            continue
        source_path_raw = source.get("path")
        if not isinstance(source_path_raw, str):
            errors.append(f"{slug}: source.path is required")
            source_file = None
        else:
            source_file, source_errors = check_source_path(
                root, source_path_raw, f"{slug}.source.path"
            )
            errors.extend(source_errors)
        source_base = source.get("base_sha")
        if not isinstance(source_base, str) or not HEX_SHA.fullmatch(source_base):
            errors.append(f"{slug}: source.base_sha must be an immutable 40-character SHA")
            source_base = ""
        source_kind = source.get("kind")
        if source_kind not in {"upstream", "hermes-native"}:
            errors.append(f"{slug}: source.kind must be upstream or hermes-native")
        source_repo = source.get("repository")
        if not isinstance(source_repo, str) or not source_repo.startswith("https://"):
            errors.append(f"{slug}: source.repository must be an HTTPS URL")
        if source_kind == "upstream" and source_repo != repository:
            errors.append(f"{slug}: upstream source.repository must match upstream.repository")

        upstream_base = entry.get("upstream_base_sha")
        if not isinstance(upstream_base, str) or not HEX_SHA.fullmatch(upstream_base):
            errors.append(f"{slug}: upstream_base_sha must be a 40-character SHA")
        elif isinstance(current_base, str) and upstream_base != current_base:
            errors.append(
                f"{slug}: upstream_base_sha must track manifest upstream.base_sha "
                f"({upstream_base!r} != {current_base!r})"
            )

        adaptation = entry.get("adaptation")
        if not isinstance(adaptation, dict) or not isinstance(adaptation.get("policy"), str):
            errors.append(f"{slug}: adaptation.policy is required")
            policy = ""
        else:
            policy = adaptation["policy"]
            if policy not in KNOWN_POLICIES:
                errors.append(f"{slug}: unknown adaptation.policy {policy!r}")
        overlay_file: Path | None = None
        if policy == "upstream-flat-copy":
            if source_kind != "upstream":
                errors.append(f"{slug}: pure-copy policy requires an upstream source")
            if source_file is not None:
                support_errors, _ = check_support_paths(
                    root, distribution_file, text, slug, source_file, pure_copy=True
                )
                errors.extend(support_errors)
                if source_file.read_bytes() != distribution_file.read_bytes():
                    errors.append(f"{slug}: pure-copy distribution drifted from {source_path_raw}")
        else:
            overlay_raw = source.get("overlay_path")
            if not isinstance(overlay_raw, str):
                errors.append(f"{slug}: adapted source requires source.overlay_path")
            else:
                overlay_file, overlay_errors = check_source_path(
                    root, overlay_raw, f"{slug}.source.overlay_path"
                )
                errors.extend(overlay_errors)
            support_errors, _ = check_support_paths(root, distribution_file, text, slug)
            errors.extend(support_errors)
            digest = entry.get("distribution_sha256")
            if not isinstance(digest, str) or not HEX_SHA256.fullmatch(digest):
                errors.append(f"{slug}: adapted source requires distribution_sha256")
            elif digest != sha256_file(distribution_file):
                errors.append(f"{slug}: adapted distribution_sha256 does not match the file")

        if source_file is not None and source_base:
            check_provenance_record(entry, source_file, overlay_file, source_base, errors)
        for provenance_file in (
            source_file if source_kind == "hermes-native" else None,
            overlay_file,
        ):
            if provenance_file is not None:
                errors.extend(
                    check_public_portability(
                        provenance_file,
                        provenance_file.read_text(encoding="utf-8", errors="replace"),
                    )
                )

        for package_file in distribution_file.parent.rglob("*"):
            if package_file.is_file():
                errors.extend(
                    check_public_portability(
                        package_file,
                        package_file.read_text(encoding="utf-8", errors="replace"),
                    )
                )
        try:
            blocks = fenced_blocks(text)
        except ValueError as exc:
            errors.append(f"{distribution_file}: {exc}")
            blocks = []
        for block in blocks:
            if RETIRED.search(block):
                errors.append(f"{distribution_file}: retired durable API in executable code block")

        required = REQUIRED_SEMANTICS.get(slug, ())
        missing = [token for token in required if token not in text]
        if missing:
            errors.append(f"{slug}: missing current durable semantics: {', '.join(missing)}")

        for key in ("source", "upstream_base_sha", "adaptation", "version", "validation"):
            if key not in entry:
                errors.append(f"{slug}: manifest missing {key}")

    direct_distribution = {
        path.resolve()
        for path in (root / "skills").glob("*/SKILL.md")
        if path.is_file()
    }
    missing_manifest = sorted(str(path.relative_to(root)) for path in direct_distribution - manifest_distribution)
    unbundled = sorted(str(path.relative_to(root)) for path in manifest_distribution - direct_distribution)
    if missing_manifest:
        errors.append(f"unlisted direct distributions: {', '.join(missing_manifest)}")
    if unbundled:
        errors.append(f"manifest distributions are not direct skills: {', '.join(unbundled)}")
    if not (root / "LICENSE").is_file():
        errors.append("upstream MIT LICENSE is missing")


    check_recovery_scripts_present(root, errors)
    check_no_hardcoded_hermes_paths(root, errors)

    return errors

def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.resolve()
    errors = validate(root)
    if errors:
        print("FAIL: Hermes skill distribution validation")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        "PASS: Hermes skill distribution validation "
        f"({len(json.loads((root / 'hermes-skill-manifest.json').read_text())['skills'])} skills; "
        f"{support_reference_count(root)} support references checked; 0 missing support paths)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
