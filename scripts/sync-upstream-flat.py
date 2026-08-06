#!/usr/bin/env python3
"""Refresh pure upstream flat copies and fail closed on adapted-source drift."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
manifest_path = ROOT / "hermes-skill-manifest.json"
manifest = json.loads(manifest_path.read_text())
base = manifest["upstream"]["base_sha"]
new = subprocess.check_output(["git", "rev-parse", "upstream/main"], text=True).strip()
changed = set(subprocess.check_output(["git", "diff", "--name-only", f"{base}..{new}"], text=True).splitlines())
print(f"upstream base: {base}")
print(f"upstream head: {new}")
errors = []
for entry in manifest["skills"]:
    source = entry["source"]
    if source["kind"] != "upstream" or not source.get("path"):
        continue
    source_path = source["path"]
    if source_path not in changed:
        continue
    print(f"mapped upstream skill changed: {entry['slug']} ({source_path})")
    if entry["adaptation"]["policy"] != "upstream-flat-copy":
        errors.append(f"adapted skill requires maintainer rebase: {entry['slug']}")
        continue
    target = ROOT / entry["distribution_path"]
    target.write_bytes((ROOT / source_path).read_bytes())

if errors:
    print("FAIL: adaptation drift detected; no adapted flat copy was overwritten", file=sys.stderr)
    print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
    sys.exit(1)

manifest["upstream"]["base_sha"] = new
for entry in manifest["skills"]:
    entry["upstream_base_sha"] = new
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
print("PASS: pure copies refreshed and manifest base advanced")
