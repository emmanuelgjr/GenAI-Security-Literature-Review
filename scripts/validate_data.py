#!/usr/bin/env python3
"""Validate literature.json and taxonomy.json against their JSON schemas."""

import json
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SCHEMA_DIR = ROOT / "schemas"


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate_file(data_path: Path, schema_path: Path) -> list[str]:
    """Validate a JSON file against its schema. Returns list of errors."""
    data = load_json(data_path)
    schema = load_json(schema_path)
    validator = jsonschema.Draft202012Validator(schema)
    errors = []
    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        path = ".".join(str(p) for p in error.absolute_path)
        errors.append(f"  {path}: {error.message}")
    return errors


def check_unique_ids(literature: dict) -> list[str]:
    """Check that all entry IDs are unique."""
    ids = [e["id"] for e in literature["entries"]]
    seen = set()
    dupes = set()
    for id_ in ids:
        if id_ in seen:
            dupes.add(id_)
        seen.add(id_)
    return [f"  Duplicate ID: {d}" for d in sorted(dupes)]


def check_category_refs(literature: dict, taxonomy: dict) -> list[str]:
    """Check that all category references in literature exist in taxonomy."""
    valid_cats = set()
    for domain in taxonomy["domains"]:
        for cat in domain["categories"]:
            valid_cats.add(cat["id"])

    errors = []
    for entry in literature["entries"]:
        for cat in entry.get("categories", []):
            if cat not in valid_cats:
                errors.append(f"  {entry['id']}: unknown category '{cat}'")
    return errors


def main():
    all_errors = []

    # Validate literature.json
    print("Validating data/literature.json...")
    errors = validate_file(DATA_DIR / "literature.json", SCHEMA_DIR / "literature-entry.schema.json")
    if errors:
        all_errors.extend(["literature.json schema errors:"] + errors)
    else:
        print("  Schema: OK")

    # Validate taxonomy.json
    print("Validating data/taxonomy.json...")
    errors = validate_file(DATA_DIR / "taxonomy.json", SCHEMA_DIR / "taxonomy.schema.json")
    if errors:
        all_errors.extend(["taxonomy.json schema errors:"] + errors)
    else:
        print("  Schema: OK")

    # Cross-validation
    literature = load_json(DATA_DIR / "literature.json")
    taxonomy = load_json(DATA_DIR / "taxonomy.json")

    print("Checking unique IDs...")
    errors = check_unique_ids(literature)
    if errors:
        all_errors.extend(["Duplicate ID errors:"] + errors)
    else:
        print(f"  {len(literature['entries'])} entries, all IDs unique")

    print("Checking category references...")
    errors = check_category_refs(literature, taxonomy)
    if errors:
        all_errors.extend(["Category reference errors:"] + errors)
    else:
        print("  All category references valid")

    if all_errors:
        print("\nVALIDATION FAILED:")
        for e in all_errors:
            print(e)
        sys.exit(1)
    else:
        print("\nAll validations passed!")


if __name__ == "__main__":
    main()
