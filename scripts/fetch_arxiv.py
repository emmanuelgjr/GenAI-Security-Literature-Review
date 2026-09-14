#!/usr/bin/env python3
"""Fetch new LLM security papers from the arXiv API.

Queries come from data/sources.json. They are OR-ed into a single request:
arXiv rate-limits aggressively (one call per three seconds, and often 429s
from shared CI runners), so one retried request beats five that each may fail.
"""

import re
import sys
from datetime import datetime, timedelta
from xml.etree.ElementTree import Element

from defusedxml import ElementTree as ET

from fetch_common import SCRIPTS_DIR, exit_code, get_with_retry, load_source, write_candidates

NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def _text(entry: Element, tag: str) -> str:
    node = entry.find(tag, NS)
    return re.sub(r"\s+", " ", node.text or "").strip() if node is not None else ""


def build_query(query_terms: list[str]) -> str:
    """Combine the configured queries into one arXiv search expression."""
    return " OR ".join(f"({term})" for term in query_terms)


def parse_feed(xml_data: bytes) -> list[dict]:
    """Turn an arXiv Atom feed into candidate papers."""
    root = ET.fromstring(xml_data)
    papers = []
    for entry in root.findall("atom:entry", NS):
        entry_id = _text(entry, "atom:id")
        if "/api/errors" in entry_id:
            # arXiv reports malformed queries as a single pseudo-entry
            raise ValueError(f"arXiv query error: {_text(entry, 'atom:summary')}")

        arxiv_id = re.sub(r"v\d+$", "", entry_id.split("/abs/")[-1])
        published = _text(entry, "atom:published")
        pdf_url = next(
            (link.get("href", "") for link in entry.findall("atom:link", NS) if link.get("title") == "pdf"),
            "",
        )
        papers.append({
            "title": _text(entry, "atom:title"),
            "authors": [_text(a, "atom:name") for a in entry.findall("atom:author", NS)],
            "year": int(published[:4]) if published else 0,
            "month": int(published[5:7]) if len(published) >= 7 else 0,
            "published": published[:10],
            "abstract": _text(entry, "atom:summary")[:500],
            "url": f"https://arxiv.org/abs/{arxiv_id}",
            "pdf_url": pdf_url or f"https://arxiv.org/pdf/{arxiv_id}",
            "doi": _text(entry, "arxiv:doi"),
            "arxiv_id": arxiv_id,
            "arxiv_categories": [c.get("term", "") for c in entry.findall("atom:category", NS)],
        })
    return papers


def main() -> int:
    config = load_source("arxiv")
    output = SCRIPTS_DIR / config["candidates_file"]
    if not config.get("enabled", True):
        print("arXiv source disabled in sources.json")
        return 0

    params = {
        "search_query": build_query(config["query_terms"]),
        "start": 0,
        "max_results": config["max_results"],
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    papers, errors = [], []
    try:
        # A weekly job can afford a few minutes of patience; a missed week cannot be recovered
        response = get_with_retry(config["api_url"], params=params, timeout=90, attempts=5, backoff=30)
        papers = parse_feed(response.content)
        print(f"arXiv returned {len(papers)} papers")
    except Exception as exc:  # report, don't crash: other sources still run
        errors.append(str(exc))
        print(f"Error: {exc}", file=sys.stderr)

    cutoff = (datetime.now() - timedelta(days=config["lookback_days"])).strftime("%Y-%m-%d")
    recent = [p for p in papers if p["published"] >= cutoff]
    print(f"{len(recent)} papers published since {cutoff}")

    write_candidates(output, "arxiv", recent, errors)
    return exit_code(recent, errors)


if __name__ == "__main__":
    sys.exit(main())
