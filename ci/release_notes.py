#!/usr/bin/env python3
"""Print one version's section from CHANGELOG.md, for GitHub release notes.

Usage: release_notes.py 0.2.0
Exits non-zero when that version has no section, so the caller can fall back.
"""

from __future__ import annotations

import pathlib
import re
import sys

# The changelog holds umlauts and typographic dashes. Write them as UTF-8 even
# where the platform default is not, so the notes survive the trip to GitHub.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: release_notes.py <version>", file=sys.stderr)
        return 2

    version = sys.argv[1]
    text = pathlib.Path("CHANGELOG.md").read_text(encoding="utf-8")

    start = re.search(rf"^## \[{re.escape(version)}\].*$", text, re.M)
    if not start:
        return 1

    rest = text[start.end():]
    end = re.search(r"^## \[", rest, re.M)
    body = (rest[: end.start()] if end else rest).strip("\n")
    if not body:
        return 1

    print(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
