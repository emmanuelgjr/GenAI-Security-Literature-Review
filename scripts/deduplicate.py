#!/usr/bin/env python3
"""Deduplicate candidate papers against existing literature and merge new entries."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from framework_mappings import category_mappings, fill_missing
from relevance import CONFIDENCE_LEVELS, auto_categorize, confidence, is_on_topic, scope_note

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SCRIPTS_DIR = ROOT / "scripts"

CANDIDATE_FILES = [
    SCRIPTS_DIR / "candidates_arxiv.json",
    SCRIPTS_DIR / "candidates_s2.json",
    SCRIPTS_DIR / "candidates_crossref.json",
]


def normalize_title(title: str) -> str:
    """Normalize title for comparison."""
    title = title.lower().strip()
    title = re.sub(r"[^a-z0-9\s]", "", title)
    title = re.sub(r"\s+", " ", title)
    return title


def title_similarity(a: str, b: str) -> float:
    """Simple Jaccard similarity between title word sets."""
    words_a = set(normalize_title(a).split())
    words_b = set(normalize_title(b).split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def build_existing_index(literature: dict) -> dict:
    """Build lookup indices from existing literature."""
    index = {
        "arxiv_ids": set(),
        "dois": set(),
        "s2_ids": set(),
        "titles": [],
    }
    for entry in literature["entries"]:
        ext = entry.get("external_ids", {})
        if ext.get("arxiv_id"):
            index["arxiv_ids"].add(ext["arxiv_id"])
        if ext.get("doi"):
            index["dois"].add(ext["doi"].lower())
        if ext.get("semantic_scholar_id"):
            index["s2_ids"].add(ext["semantic_scholar_id"])
        if entry.get("doi"):
            index["dois"].add(entry["doi"].lower())
        index["titles"].append(normalize_title(entry["title"]))
    return index


def is_duplicate(paper: dict, index: dict) -> bool:
    """Check if a paper is a duplicate of an existing entry."""
    # Check arXiv ID
    if paper.get("arxiv_id") and paper["arxiv_id"] in index["arxiv_ids"]:
        return True

    # Check DOI
    if paper.get("doi") and paper["doi"].lower() in index["dois"]:
        return True

    # Check Semantic Scholar ID
    if paper.get("semantic_scholar_id") and paper["semantic_scholar_id"] in index["s2_ids"]:
        return True

    # Check title similarity
    norm_title = normalize_title(paper.get("title", ""))
    for existing_title in index["titles"]:
        if title_similarity(norm_title, existing_title) > 0.85:
            return True

    return False


def add_to_index(paper: dict, index: dict) -> None:
    """Record a newly accepted paper so later candidates dedup against it."""
    if paper.get("arxiv_id"):
        index["arxiv_ids"].add(paper["arxiv_id"])
    if paper.get("doi"):
        index["dois"].add(paper["doi"].lower())
    if paper.get("semantic_scholar_id"):
        index["s2_ids"].add(paper["semantic_scholar_id"])
    index["titles"].append(normalize_title(paper.get("title", "")))


def entry_lookup_keys(entry: dict) -> dict:
    """Flatten a literature entry into the candidate-paper shape is_duplicate expects."""
    ext = entry.get("external_ids", {})
    return {
        "title": entry.get("title", ""),
        "doi": entry.get("doi") or ext.get("doi", ""),
        "arxiv_id": ext.get("arxiv_id", ""),
        "semantic_scholar_id": ext.get("semantic_scholar_id", ""),
    }


def pending_entries(pending: dict, index: dict, base: dict | None = None) -> list[dict]:
    """Entries the open auto-fetch PR adds that main does not have yet.

    The weekly run rebuilds that PR from main, so without this anything found in
    an earlier week and not yet merged would silently drop off the PR. Entries
    are kept verbatim (a reviewer may have fixed categories on the branch); only
    their IDs are reassigned by the caller.

    `base` is literature.json at the PR's merge base. Entries already there were
    inherited from main rather than added by the PR, so if main has since
    deleted them they must stay deleted, not be carried back in.
    """
    base_index = build_existing_index(base) if base else None
    kept = []
    for entry in pending.get("entries", []):
        keys = entry_lookup_keys(entry)
        if is_duplicate(keys, index) or (base_index and is_duplicate(keys, base_index)):
            continue
        add_to_index(keys, index)
        kept.append(dict(entry))
    return kept


def get_next_id(literature: dict) -> int:
    """Get the next sequential ID number."""
    max_num = 0
    for entry in literature["entries"]:
        match = re.search(r"-(\d{5})$", entry["id"])
        if match:
            max_num = max(max_num, int(match.group(1)))
    return max_num + 1


YEAR_MIN = 2017
YEAR_MAX = datetime.now().year + 1


def is_valid_candidate(paper: dict) -> tuple[bool, str]:
    """Reject candidates that would fail schema validation."""
    year = paper.get("year")
    if not isinstance(year, int) or year < YEAR_MIN or year > YEAR_MAX:
        return False, f"year={year!r} outside [{YEAR_MIN},{YEAR_MAX}]"
    authors = paper.get("authors") or []
    if not authors:
        return False, "empty authors"
    title = (paper.get("title") or "").strip()
    if not title:
        return False, "empty title"
    url = (paper.get("url") or "").strip()
    if not url:
        return False, "empty url"
    return True, ""


def paper_to_entry(paper: dict, entry_id: str, source: str, mappings: dict | None = None) -> dict:
    """Convert a candidate paper to a literature entry.

    `mappings` (see framework_mappings.category_mappings) adds suggested
    framework mappings derived from the entry's categories.
    """
    entry = {
        "id": entry_id,
        "type": "paper",
        "title": paper["title"],
        "authors": paper.get("authors", []),
        "year": paper.get("year", 0),
        "url": paper.get("url", ""),
        "categories": [],
        "added_date": datetime.now().strftime("%Y-%m-%d"),
        "added_by": "automation",
        "source_api": source,
        "external_ids": {},
        "reviewed": False,
    }

    if paper.get("month"):
        entry["month"] = paper["month"]
    if paper.get("venue"):
        entry["venue"] = paper["venue"]
    if paper.get("abstract"):
        entry["abstract"] = paper["abstract"]
    if paper.get("doi"):
        entry["doi"] = paper["doi"]
        entry["external_ids"]["doi"] = paper["doi"]
    if paper.get("pdf_url"):
        entry["pdf_url"] = paper["pdf_url"]
    if paper.get("arxiv_id"):
        entry["external_ids"]["arxiv_id"] = paper["arxiv_id"]
    if paper.get("semantic_scholar_id"):
        entry["external_ids"]["semantic_scholar_id"] = paper["semantic_scholar_id"]
    if paper.get("citation_count"):
        entry["citation_count"] = paper["citation_count"]
    if paper.get("open_access") is not None:
        entry["open_access"] = paper["open_access"]

    # Auto-categorize based on title/abstract keywords
    text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
    categories = auto_categorize(text)
    entry["categories"] = categories
    fill_missing(entry, mappings or {})

    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pending",
        type=Path,
        help="literature.json from the open auto-fetch PR branch; its unmerged entries are carried over",
    )
    parser.add_argument(
        "--pending-base",
        type=Path,
        help="literature.json at the merge base of that branch and main (see pending_entries)",
    )
    args = parser.parse_args()

    # Load existing literature
    lit_path = DATA_DIR / "literature.json"
    with open(lit_path, encoding="utf-8") as f:
        literature = json.load(f)

    with open(DATA_DIR / "taxonomy.json", encoding="utf-8") as f:
        mappings = category_mappings(json.load(f))

    index = build_existing_index(literature)
    next_num = get_next_id(literature)
    year = datetime.now().year

    new_entries = []
    seen_in_candidates = set()

    if args.pending and args.pending.exists():
        base = None
        if args.pending_base and args.pending_base.exists():
            with open(args.pending_base, encoding="utf-8") as f:
                base = json.load(f)
        with open(args.pending, encoding="utf-8") as f:
            carried = pending_entries(json.load(f), index, base)
        for entry in carried:
            entry["id"] = f"llmsec-{year}-{next_num:05d}"
            fill_missing(entry, mappings)
            next_num += 1
            seen_in_candidates.add(normalize_title(entry["title"]))
        new_entries.extend(carried)
        print(f"Carried over {len(carried)} unmerged entries from {args.pending.name}")

    for cand_file in CANDIDATE_FILES:
        if not cand_file.exists():
            print(f"Skipping {cand_file.name} (not found)")
            continue

        with open(cand_file, encoding="utf-8") as f:
            candidates = json.load(f)

        source = candidates.get("source", "manual")
        papers = candidates.get("papers", [])
        print(f"\nProcessing {cand_file.name}: {len(papers)} candidates from {source}")

        added = 0
        skipped_invalid = 0
        skipped_offtopic = 0
        for paper in papers:
            # Drop candidates that would fail schema validation
            ok, reason = is_valid_candidate(paper)
            if not ok:
                skipped_invalid += 1
                continue

            # Drop candidates that are not about GenAI security (see is_on_topic)
            if not is_on_topic(paper):
                skipped_offtopic += 1
                continue

            # Check against existing
            if is_duplicate(paper, index):
                continue

            # Check against other candidates in this batch
            norm = normalize_title(paper.get("title", ""))
            if norm in seen_in_candidates:
                continue
            seen_in_candidates.add(norm)

            entry_id = f"llmsec-{year}-{next_num:05d}"
            entry = paper_to_entry(paper, entry_id, source, mappings)
            new_entries.append(entry)
            next_num += 1
            added += 1

            # Update index for subsequent dedup
            add_to_index(paper, index)

        print(f"  Added {added} new entries (skipped {skipped_invalid} invalid, {skipped_offtopic} off-topic)")

    if not new_entries:
        print("\nNo new entries to add.")
        sys.exit(0)

    # Merge into literature
    literature["entries"].extend(new_entries)

    with open(lit_path, "w", encoding="utf-8") as f:
        json.dump(literature, f, indent=2, ensure_ascii=False)

    print(f"\nAdded {len(new_entries)} new entries. Total: {len(literature['entries'])}")

    print("\n--- New Entries ---")
    print(review_summary(new_entries))


def review_summary(entries: list[dict]) -> str:
    """PR summary grouped by confidence, weakest matches first, with scope hints."""
    lines = []
    for level in CONFIDENCE_LEVELS:
        group = [e for e in entries if confidence(e) == level]
        if not group:
            continue
        lines.append(f"## {level.capitalize()} confidence ({len(group)})")
        for entry in group:
            note = scope_note(entry)
            lines.append(f"- [{entry['id']}] {entry['title']}")
            lines.append(f"  {entry['url']}")
            lines.append(f"  Categories: {', '.join(entry['categories'])}" + (f"  <- {note}" if note else ""))
        lines.append("")
    return "\n".join(lines).rstrip()


if __name__ == "__main__":
    main()
