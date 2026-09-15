#!/usr/bin/env python3
"""Suggest framework mappings (OWASP, MITRE ATLAS, NIST) for entries from their categories.

Categories in data/taxonomy.json may carry `framework_mappings` for links that
hold for essentially every paper in the category (prompt-injection -> LLM01 /
AML.T0051). Automated entries get the union of their categories' mappings so
they show up in the webapp's framework explorer; like everything else about
them, the suggestion is subject to review (`reviewed: false`).

Run with --backfill to fill in unmapped, unreviewed automated entries in
data/literature.json.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TAXONOMY = ROOT / "data" / "taxonomy.json"
LITERATURE = ROOT / "data" / "literature.json"


def category_mappings(taxonomy: dict) -> dict[str, dict[str, list[str]]]:
    """category id -> {framework id: [entry ids]} for categories that define mappings."""
    return {
        category["id"]: category["framework_mappings"]
        for domain in taxonomy["domains"]
        for category in domain["categories"]
        if category.get("framework_mappings")
    }


def suggest(categories: list[str], mappings: dict[str, dict[str, list[str]]]) -> dict[str, list[str]]:
    """Union of the mappings of the given categories, with stable ordering."""
    merged: dict[str, list[str]] = {}
    for category in categories:
        for framework, ids in mappings.get(category, {}).items():
            bucket = merged.setdefault(framework, [])
            bucket.extend(i for i in ids if i not in bucket)
    return {framework: sorted(ids) for framework, ids in sorted(merged.items())}


def fill_missing(entry: dict, mappings: dict[str, dict[str, list[str]]]) -> bool:
    """Add suggested mappings to an entry that has none. Returns True if it changed."""
    if entry.get("framework_mappings"):
        return False
    suggested = suggest(entry.get("categories", []), mappings)
    if not suggested:
        return False
    entry["framework_mappings"] = suggested
    return True


def backfill(literature: dict, taxonomy: dict) -> int:
    """Fill mappings on unreviewed automated entries only; curated ones are left alone."""
    mappings = category_mappings(taxonomy)
    return sum(
        fill_missing(entry, mappings)
        for entry in literature["entries"]
        if entry.get("added_by") == "automation" and not entry.get("reviewed")
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--backfill", action="store_true", help="update data/literature.json in place")
    args = parser.parse_args()
    if not args.backfill:
        parser.print_help()
        return
    raw = LITERATURE.read_text(encoding="utf-8")
    literature = json.loads(raw)
    taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    changed = backfill(literature, taxonomy)
    trailing = "\n" if raw.endswith("\n") else ""
    LITERATURE.write_text(json.dumps(literature, indent=2, ensure_ascii=False) + trailing, encoding="utf-8", newline="\n")
    print(f"Added framework mappings to {changed} entries")


if __name__ == "__main__":
    main()
