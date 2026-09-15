#!/usr/bin/env python3
"""Validate data/*.json against the schemas and against each other."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

import jsonschema

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SCHEMA_DIR = ROOT / "schemas"


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def schema_errors(data: dict, schema: dict) -> list[str]:
    """Schema violations, including "format" (dates), which jsonschema skips by default."""
    validator = jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER
    )
    return [
        f"  {'.'.join(str(p) for p in error.absolute_path)}: {error.message}"
        for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path))
    ]


def check_unique_ids(literature: dict) -> list[str]:
    """Check that all entry IDs are unique."""
    seen, dupes = set(), set()
    for entry_id in (e["id"] for e in literature["entries"]):
        if entry_id in seen:
            dupes.add(entry_id)
        seen.add(entry_id)
    return [f"  Duplicate ID: {d}" for d in sorted(dupes)]


def check_duplicate_resources(literature: dict) -> list[str]:
    """The same paper added twice under different IDs, detected by arXiv ID or DOI."""
    owners: dict[tuple[str, str], list[str]] = defaultdict(list)
    for entry in literature["entries"]:
        ext = entry.get("external_ids", {})
        doi = (entry.get("doi") or ext.get("doi") or "").lower()
        for key in (("arXiv", ext.get("arxiv_id", "")), ("DOI", doi)):
            if key[1] and entry["id"] not in owners[key]:
                owners[key].append(entry["id"])
    return [
        f"  {kind} {value} appears in {', '.join(ids)}"
        for (kind, value), ids in sorted(owners.items())
        if len(ids) > 1
    ]


def check_urls(literature: dict) -> list[str]:
    """url/pdf_url must be absolute http(s) links (the schema's "uri" format needs an extra package)."""
    errors = []
    for entry in literature["entries"]:
        for field in ("url", "pdf_url"):
            value = entry.get(field)
            if value is None:
                continue
            parsed = urlparse(value)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                errors.append(f"  {entry['id']}: {field} is not an http(s) URL: {value!r}")
    return errors


def check_category_refs(literature: dict, taxonomy: dict) -> list[str]:
    """Check that all category references in literature exist in taxonomy."""
    valid_cats = {cat["id"] for domain in taxonomy["domains"] for cat in domain["categories"]}
    return [
        f"  {entry['id']}: unknown category '{cat}'"
        for entry in literature["entries"]
        for cat in entry.get("categories", [])
        if cat not in valid_cats
    ]


def check_framework_refs(literature: dict, taxonomy: dict, frameworks: dict) -> list[str]:
    """Framework mapping IDs on entries and taxonomy categories must exist in frameworks.json."""
    known = {f["id"]: {e["id"] for e in f["entries"]} for f in frameworks["frameworks"]}
    owners = [(e["id"], e.get("framework_mappings") or {}) for e in literature["entries"]]
    owners += [
        (f"taxonomy:{cat['id']}", cat.get("framework_mappings") or {})
        for domain in taxonomy["domains"]
        for cat in domain["categories"]
    ]
    errors = []
    for owner, mappings in owners:
        for framework, ids in mappings.items():
            if framework not in known:
                errors.append(f"  {owner}: unknown framework '{framework}'")
                continue
            errors.extend(
                f"  {owner}: unknown {framework} entry '{i}'" for i in ids if i not in known[framework]
            )
    return errors


def main() -> int:
    literature = load_json(DATA_DIR / "literature.json")
    taxonomy = load_json(DATA_DIR / "taxonomy.json")
    frameworks = load_json(DATA_DIR / "frameworks.json")

    checks = [
        ("literature.json schema", lambda: schema_errors(literature, load_json(SCHEMA_DIR / "literature-entry.schema.json"))),
        ("taxonomy.json schema", lambda: schema_errors(taxonomy, load_json(SCHEMA_DIR / "taxonomy.schema.json"))),
        ("unique IDs", lambda: check_unique_ids(literature)),
        ("duplicate resources", lambda: check_duplicate_resources(literature)),
        ("URLs", lambda: check_urls(literature)),
        ("category references", lambda: check_category_refs(literature, taxonomy)),
        ("framework references", lambda: check_framework_refs(literature, taxonomy, frameworks)),
    ]

    failed = False
    for name, run in checks:
        errors = run()
        print(f"{'FAIL' if errors else 'ok  '} {name}")
        for error in errors:
            print(error)
        failed = failed or bool(errors)

    print(f"\n{len(literature['entries'])} entries: " + ("VALIDATION FAILED" if failed else "All validations passed!"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
