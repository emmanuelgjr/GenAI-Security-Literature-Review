#!/usr/bin/env python3
"""Fetch new LLM security papers from CrossRef API."""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = ROOT / "scripts" / "candidates_crossref.json"

CROSSREF_API = "https://api.crossref.org/works"

QUERIES = [
    "large language model security",
    "LLM prompt injection attack",
    "AI safety adversarial machine learning",
]

MAX_RESULTS_PER_QUERY = 30


def fetch_query(query: str, max_results: int = MAX_RESULTS_PER_QUERY) -> list[dict]:
    """Fetch papers from CrossRef for a single query."""
    params = {
        "query": query,
        "rows": max_results,
        "filter": "has-abstract:true",
        "sort": "published",
        "order": "desc",
        "select": "DOI,title,author,published-print,published-online,abstract,URL,is-referenced-by-count",
    }
    headers = {
        "User-Agent": "LLMSecLitReview/1.0 (mailto:emmanuelgjr@gmail.com)",
    }

    resp = requests.get(CROSSREF_API, params=params, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    papers = []
    for item in data.get("message", {}).get("items", []):
        title_list = item.get("title", [])
        title = title_list[0] if title_list else ""
        if not title:
            continue

        authors = []
        for a in item.get("author", []):
            name = f"{a.get('given', '')} {a.get('family', '')}".strip()
            if name:
                authors.append(name)

        doi = item.get("DOI", "")

        # Get year/month from published date
        pub = item.get("published-online") or item.get("published-print") or {}
        date_parts = pub.get("date-parts", [[0]])[0]
        year = date_parts[0] if len(date_parts) > 0 else 0
        month = date_parts[1] if len(date_parts) > 1 else 0

        abstract = (item.get("abstract") or "")[:500]
        # Strip JATS XML tags from abstract
        import re
        abstract = re.sub(r"<[^>]+>", "", abstract)

        citation_count = item.get("is-referenced-by-count", 0)

        papers.append({
            "title": title,
            "authors": authors,
            "year": year,
            "month": month,
            "abstract": abstract,
            "url": item.get("URL", f"https://doi.org/{doi}"),
            "doi": doi,
            "citation_count": citation_count,
            "venue": "",
        })

    return papers


def main():
    all_papers = []
    seen_dois = set()

    for i, query in enumerate(QUERIES):
        print(f"Query {i+1}/{len(QUERIES)}: {query}...")
        try:
            papers = fetch_query(query)
            for p in papers:
                key = p["doi"] or p["title"].lower()
                if key not in seen_dois:
                    seen_dois.add(key)
                    all_papers.append(p)
            print(f"  Found {len(papers)} papers ({len(all_papers)} unique total)")
        except Exception as e:
            print(f"  Error: {e}", file=sys.stderr)

        if i < len(QUERIES) - 1:
            time.sleep(2)

    # Filter to recent (2023+)
    filtered = [p for p in all_papers if p["year"] >= 2023]

    print(f"\n{len(filtered)} papers from 2023+ (from {len(all_papers)} total)")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({"source": "crossref", "fetched_at": datetime.now().isoformat(), "papers": filtered}, f, indent=2)

    print(f"Written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
