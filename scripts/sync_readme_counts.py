#!/usr/bin/env python3
"""Keep the resource counts in README.md in step with data/.

The weekly fetch adds entries, so any count hard-coded in the README goes
stale the moment a PR merges. This rewrites those numbers from the data
files. Run with --check to fail instead of writing, for CI.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
LITERATURE = ROOT / "data" / "literature.json"
TAXONOMY = ROOT / "data" / "taxonomy.json"

# "tracking **244 resources** across **43 of 46 categories**"
SUMMARY_RE = re.compile(
    r"(tracking \*\*)\d+( resources\*\* across \*\*)(?:\d+ of )?\d+( categories\*\*)"
)
# "literature.json      # Core database (244 curated entries)"
STRUCTURE_RE = re.compile(r"(literature\.json\s+# Core database \()\d+( curated entries\))")
# "taxonomy.json        # 8 domains, 46 category definitions"
TAXONOMY_RE = re.compile(r"(taxonomy\.json\s+# )\d+( domains, )\d+( category definitions\))?")


def counts() -> tuple[int, int, int, int]:
    entries = json.loads(LITERATURE.read_text(encoding="utf-8"))["entries"]
    domains = json.loads(TAXONOMY.read_text(encoding="utf-8"))["domains"]

    defined = sum(len(d.get("categories", [])) for d in domains)
    used = set()
    for entry in entries:
        value = entry.get("category", entry.get("categories", []))
        used.update([value] if isinstance(value, str) else value)

    return len(entries), len(used), defined, len(domains)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero if the README is out of date instead of rewriting it",
    )
    args = parser.parse_args()

    total, used, defined, domains = counts()
    original = README.read_text(encoding="utf-8")

    updated = SUMMARY_RE.sub(rf"\g<1>{total}\g<2>{used} of {defined}\g<3>", original)
    updated = STRUCTURE_RE.sub(rf"\g<1>{total}\g<2>", updated)
    updated = re.sub(
        r"(taxonomy\.json\s+# )\d+( domains, )\d+( category definitions)",
        rf"\g<1>{domains}\g<2>{defined}\g<3>",
        updated,
    )

    label = f"{total} resources, {used} of {defined} categories in use, {domains} domains"

    if updated == original:
        print(f"README already in sync ({label})")
        return 0

    if args.check:
        print(f"README is out of date. Expected: {label}", file=sys.stderr)
        print("Run: python scripts/sync_readme_counts.py", file=sys.stderr)
        return 1

    README.write_text(updated, encoding="utf-8")
    print(f"README updated ({label})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
