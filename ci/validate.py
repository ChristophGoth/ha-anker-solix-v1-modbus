#!/usr/bin/env python3
"""Pre-release checks for the integration.

Run by the `validate` job. Catches the mistakes that only surface after a
release is published: malformed JSON, a manifest missing a key Home Assistant
needs, translations that have drifted apart from strings.json, and a tag whose
version does not match the manifest it ships.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

ROOT = pathlib.Path(os.environ.get("INTEGRATION_PATH", "custom_components/anker_solix_v1"))


def main() -> int:
    failures: list[str] = []

    for path in sorted(pathlib.Path(".").rglob("*.json")):
        if ".git" in path.parts:
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"{path}: {exc}")
    if failures:
        print("invalid JSON:", *failures, sep="\n  ")
        return 1

    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    for key in ("domain", "name", "version", "documentation", "codeowners"):
        if not manifest.get(key):
            failures.append(f"manifest.json is missing {key!r}")

    # Home Assistant resolves a sensor's translated states through its options
    # list; a missing entry shows a raw key instead of a name.
    strings = json.loads((ROOT / "strings.json").read_text(encoding="utf-8"))
    for lang in ("en", "de"):
        path = ROOT / "translations" / f"{lang}.json"
        other = json.loads(path.read_text(encoding="utf-8"))
        for platform, entities in strings.get("entity", {}).items():
            theirs = other.get("entity", {}).get(platform, {})
            missing = set(entities) - set(theirs)
            if missing:
                failures.append(f"{path}: {platform} lacks {sorted(missing)}")
            for key, spec in entities.items():
                want = set(spec.get("state", {}))
                got = set(theirs.get(key, {}).get("state", {}))
                if want != got:
                    failures.append(
                        f"{path}: {platform}.{key} states differ "
                        f"(missing {sorted(want - got)}, extra {sorted(got - want)})"
                    )

    # A release must ship the version it claims in its tag.
    tag = os.environ.get("CI_COMMIT_TAG")
    if tag:
        expected = tag.lstrip("v")
        if manifest["version"] != expected:
            failures.append(
                f"tag {tag} expects manifest version {expected!r}, "
                f"found {manifest['version']!r}"
            )

    if failures:
        print("validation failed:", *failures, sep="\n  ")
        return 1

    print(f"manifest {manifest['version']} ok; JSON and translations consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
