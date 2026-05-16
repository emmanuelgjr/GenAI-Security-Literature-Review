#!/usr/bin/env python3
"""Backfill DOIs for paper and book entries in data/literature.json.

Strategy per entry (only entries of type=paper or type=book that are missing
both `doi` and `external_ids.doi` are touched):

1. If `external_ids.arxiv_id` is present, look up the arXiv metadata and
   pull `<arxiv:doi>` if arXiv has it (only set for papers that were also
   formally published).
2. Otherwise, query CrossRef by bibliographic title and accept the first
   result whose normalized-title Jaccard similarity >= 0.85 and year is
   within +/-1 of the entry year.

When a DOI is found it is written to both `entry["doi"]` (top-level,
matching the schema's existing convention) and `entry["external_ids"]["doi"]`
to stay consistent with how other indexes are populated.

The script is idempotent -- entries that already have a DOI are skipped.
Re-run safely after new entries land.

Usage: python scripts/backfill_dois.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIT_PATH = ROOT / "data" / "literature.json"

ARXIV_API = "https://export.arxiv.org/api/query"
CROSSREF_API = "https://api.crossref.org/works"
ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

USER_AGENT = "GenAI-Security-Literature-Review/1.0 (mailto:emmanuelgjr@gmail.com)"

ARXIV_DELAY_SEC = 3.0  # arXiv requests >=3s between requests
CROSSREF_DELAY_SEC = 1.0
HTTP_TIMEOUT = 30


def normalize_title(title: str) -> str:
    title = title.lower().strip()
    title = re.sub(r"[^a-z0-9\s]", "", title)
    title = re.sub(r"\s+", " ", title)
    return title


def title_jaccard(a: str, b: str) -> float:
    sa, sb = set(normalize_title(a).split()), set(normalize_title(b).split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        return resp.read()


def arxiv_lookup_doi(arxiv_id: str) -> str | None:
    """Return the DOI arXiv has for `arxiv_id`, or None if absent."""
    url = f"{ARXIV_API}?id_list={urllib.parse.quote(arxiv_id)}"
    xml_data = http_get(url)
    root = ET.fromstring(xml_data)
    entry = root.find("atom:entry", ARXIV_NS)
    if entry is None:
        return None
    doi_el = entry.find("arxiv:doi", ARXIV_NS)
    if doi_el is None or not (doi_el.text or "").strip():
        return None
    return doi_el.text.strip()


def crossref_lookup_doi(title: str, year: int | None) -> str | None:
    """Search CrossRef for `title`; return DOI of first close match (or None)."""
    params = urllib.parse.urlencode({
        "query.bibliographic": title,
        "rows": 5,
        "select": "DOI,title,issued",
    })
    url = f"{CROSSREF_API}?{params}"
    data = json.loads(http_get(url).decode("utf-8"))
    items = data.get("message", {}).get("items", [])

    for item in items:
        cand_titles = item.get("title", [])
        if not cand_titles:
            continue
        cand_title = cand_titles[0]
        if title_jaccard(title, cand_title) < 0.85:
            continue
        if year is not None:
            issued = item.get("issued", {}).get("date-parts", [[None]])[0]
            cand_year = issued[0] if issued else None
            if cand_year is not None and abs(cand_year - year) > 1:
                continue
        doi = item.get("DOI")
        if doi:
            return doi
    return None


def set_doi(entry: dict, doi: str) -> None:
    entry["doi"] = doi
    entry.setdefault("external_ids", {})["doi"] = doi


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would change but do not write the file")
    args = parser.parse_args()

    with open(LIT_PATH, encoding="utf-8") as f:
        literature = json.load(f)

    candidates = [
        e for e in literature["entries"]
        if e["type"] in ("paper", "book")
        and not e.get("doi")
        and not e.get("external_ids", {}).get("doi")
    ]

    print(f"{len(candidates)} candidates need a DOI lookup")

    found_arxiv = 0
    found_crossref = 0
    not_found = 0
    last_arxiv = 0.0
    last_crossref = 0.0

    for i, entry in enumerate(candidates, start=1):
        arxiv_id = entry.get("external_ids", {}).get("arxiv_id")
        title = entry["title"]
        year = entry.get("year")
        prefix = f"[{i:3d}/{len(candidates)}] {entry['id']}"

        doi: str | None = None
        source: str | None = None

        if arxiv_id:
            wait = ARXIV_DELAY_SEC - (time.monotonic() - last_arxiv)
            if wait > 0:
                time.sleep(wait)
            try:
                doi = arxiv_lookup_doi(arxiv_id)
            except Exception as e:  # noqa: BLE001
                print(f"{prefix} arXiv lookup error: {e}", file=sys.stderr)
            last_arxiv = time.monotonic()
            if doi:
                source = "arxiv"
                found_arxiv += 1

        if not doi:
            wait = CROSSREF_DELAY_SEC - (time.monotonic() - last_crossref)
            if wait > 0:
                time.sleep(wait)
            try:
                doi = crossref_lookup_doi(title, year)
            except Exception as e:  # noqa: BLE001
                print(f"{prefix} CrossRef lookup error: {e}", file=sys.stderr)
            last_crossref = time.monotonic()
            if doi:
                source = "crossref"
                found_crossref += 1

        if doi:
            set_doi(entry, doi)
            print(f"{prefix} OK ({source}): {doi}  -- {title[:70]}")
        else:
            not_found += 1
            print(f"{prefix} no DOI found  -- {title[:70]}")

    print(
        f"\nDone. Filled {found_arxiv + found_crossref}/{len(candidates)} "
        f"(arXiv: {found_arxiv}, CrossRef: {found_crossref}, not found: {not_found})"
    )

    if args.dry_run:
        print("Dry run -- not writing literature.json")
        return 0

    if found_arxiv + found_crossref == 0:
        print("No changes to write.")
        return 0

    with open(LIT_PATH, "w", encoding="utf-8") as f:
        json.dump(literature, f, indent=2, ensure_ascii=False)
    print(f"Updated {LIT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
