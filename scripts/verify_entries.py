#!/usr/bin/env python3
"""Check that entries' arXiv IDs and DOIs point at the papers they claim to be.

For each selected entry the authoritative title is fetched (arXiv via OAI-PMH
GetRecord, DOIs via CrossRef) and compared with the entry's title. A mismatch
usually means a wrong identifier (a real title attached to someone else's
paper); a missing record means the identifier does not exist.

By default only curated (added_by: manual) entries are checked: automated
entries take their identifiers straight from the source APIs.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import requests

from deduplicate import title_similarity
from fetch_arxiv import parse_records
from fetch_common import get_with_retry

ROOT = Path(__file__).resolve().parent.parent
LITERATURE = ROOT / "data" / "literature.json"
OAI_URL = "https://oaipmh.arxiv.org/oai"
CROSSREF_URL = "https://api.crossref.org/works/"
MATCH_THRESHOLD = 0.6  # Jaccard on title words; tolerant of subtitles and version renames
AUTHOR_THRESHOLD = 0.5  # share of claimed author surnames found at the source
ORG_WORDS = re.compile(r"\b(?:team|foundation|institute|corporation|inc|ltd|group|project|agency|national|university|google|microsoft|openai|anthropic|nist|owasp|mitre)\b", re.I)


@dataclass
class Finding:
    entry_id: str
    title: str
    identifier: str
    problem: str
    found_title: str = ""  # title (and authors) at the source


def arxiv_id_of(entry: dict) -> str:
    ext_id = (entry.get("external_ids") or {}).get("arxiv_id", "")
    if ext_id:
        return ext_id
    match = re.search(r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5}|[a-z-]+/[0-9]{7})", entry.get("url", ""))
    return match.group(1) if match else ""


def doi_of(entry: dict) -> str:
    return entry.get("doi") or (entry.get("external_ids") or {}).get("doi", "")


def arxiv_record(arxiv_id: str) -> tuple[str, list[str]] | None:
    """(title, authors) for an arXiv ID, or None if the ID does not exist."""
    params = {"verb": "GetRecord", "identifier": f"oai:arXiv.org:{arxiv_id}", "metadataPrefix": "arXiv"}
    try:
        papers, _ = parse_records(get_with_retry(OAI_URL, params=params, attempts=3, backoff=10).content)
    except ValueError:  # OAI "idDoesNotExist"
        return None
    return (papers[0]["title"], papers[0]["authors"]) if papers else None


def crossref_record(doi: str) -> tuple[str, list[str]] | None:
    """(title, authors) for a DOI registered with CrossRef, or None if unknown."""
    try:
        message = get_with_retry(CROSSREF_URL + doi, attempts=3, backoff=5).json().get("message", {})
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            return None
        raise
    titles = message.get("title") or [""]
    authors = [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in message.get("author", [])]
    return titles[0], [a for a in authors if a]


def _fold(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


def author_overlap(claimed: list[str], actual: list[str]) -> float | None:
    """Share of claimed authors whose surname appears among the actual authors.

    None when there is nothing to compare (organisations as authors, or no
    author data at the source).
    """
    people = [a for a in claimed if len(a.split()) >= 2 and not ORG_WORDS.search(a)]
    if not people or not actual:
        return None
    haystack = " ".join(_fold(a) for a in actual)
    hits = sum(1 for a in people if re.search(rf"\b{re.escape(_fold(a.split()[-1]))}\b", haystack))
    return hits / len(people)


def verify(entry: dict, sleep=time.sleep) -> list[Finding]:
    findings = []
    checks = []
    if arxiv_id := arxiv_id_of(entry):
        checks.append((f"arXiv:{arxiv_id}", lambda: arxiv_record(arxiv_id)))
    if doi := doi_of(entry):
        checks.append((f"doi:{doi}", lambda: crossref_record(doi)))
    for identifier, lookup in checks:
        record = lookup()
        if record is None:
            findings.append(Finding(entry["id"], entry["title"], identifier, "identifier not found"))
        else:
            title, authors = record
            if title and title_similarity(entry["title"], title) < MATCH_THRESHOLD:
                findings.append(Finding(entry["id"], entry["title"], identifier, "title mismatch", title))
            overlap = author_overlap(entry.get("authors", []), authors)
            if overlap is not None and overlap < AUTHOR_THRESHOLD:
                found = f"{title} -- by {', '.join(authors[:4])}{' et al.' if len(authors) > 4 else ''}"
                findings.append(Finding(entry["id"], entry["title"], identifier, "author mismatch", found))
        sleep(3)  # be polite to arXiv and CrossRef
    return findings


def report(findings: list[Finding], checked: int) -> str:
    lines = [f"Verified identifiers on {checked} entries: **{len(findings)} problem(s)**."]
    if findings:
        lines += ["", "| Entry | Identifier | Problem | Title in entry | Title at source |", "|---|---|---|---|---|"]
        for f in findings:
            cell = lambda s: s.replace("|", "\\|")[:90]  # noqa: E731
            lines.append(f"| `{f.entry_id}` | {f.identifier} | {f.problem} | {cell(f.title)} | {cell(f.found_title)} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--all", action="store_true", help="also check automated entries")
    parser.add_argument("--output", type=Path, default=Path("verify_report.md"))
    args = parser.parse_args()

    entries = json.loads(LITERATURE.read_text(encoding="utf-8"))["entries"]
    selected = [
        e for e in entries
        if (args.all or e.get("added_by") == "manual") and (arxiv_id_of(e) or doi_of(e))
    ]
    findings = []
    for i, entry in enumerate(selected, 1):
        found = verify(entry)
        findings.extend(found)
        print(f"[{i}/{len(selected)}] {entry['id']}: {'; '.join(f.problem for f in found) or 'ok'}")
    args.output.write_text(report(findings, len(selected)), encoding="utf-8")
    print(f"{len(findings)} problem(s); report in {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
