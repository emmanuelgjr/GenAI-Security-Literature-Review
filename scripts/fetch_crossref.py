#!/usr/bin/env python3
"""Fetch new LLM security papers from the CrossRef API (queries in data/sources.json)."""

import html
import re
import sys
import time
from datetime import datetime, timedelta

from fetch_common import SCRIPTS_DIR, exit_code, get_with_retry, load_source, write_candidates

# CrossRef's "polite pool" asks clients to identify themselves with a contact address.
HEADERS = {"User-Agent": "LLMSecLitReview/1.0 (mailto:emmanuelgjr@gmail.com)"}


def clean_text(value: str) -> str:
    """Strip JATS/HTML markup and entities that CrossRef leaves in titles and abstracts."""
    # Unescape first: some records double-encode markup as "&lt;b&gt;".
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(value))).strip()


def parse_items(items: list[dict]) -> list[dict]:
    """Turn CrossRef work records into candidate papers."""
    papers = []
    for item in items:
        titles = item.get("title") or []
        title = clean_text(titles[0]) if titles else ""
        if not title:
            continue
        doi = item.get("DOI", "")
        pub = item.get("published-online") or item.get("published-print") or {}
        date_parts = (pub.get("date-parts") or [[0]])[0]
        venues = item.get("container-title") or []
        papers.append({
            "title": title,
            "authors": [
                name
                for a in item.get("author", [])
                if (name := f"{a.get('given', '')} {a.get('family', '')}".strip())
            ],
            "year": date_parts[0] if date_parts else 0,
            "month": date_parts[1] if len(date_parts) > 1 else 0,
            "abstract": clean_text(item.get("abstract") or "")[:500],
            "url": item.get("URL") or f"https://doi.org/{doi}",
            "doi": doi,
            "citation_count": item.get("is-referenced-by-count", 0),
            "venue": clean_text(venues[0]) if venues else "",
        })
    return papers


def main() -> int:
    config = load_source("crossref")
    output = SCRIPTS_DIR / config["candidates_file"]
    if not config.get("enabled", True):
        print("CrossRef source disabled in sources.json")
        return 0

    from_date = (datetime.now() - timedelta(days=config["lookback_days"])).strftime("%Y-%m-%d")
    papers, errors, seen = [], [], set()
    for i, query in enumerate(config["query_terms"]):
        print(f"Query {i + 1}/{len(config['query_terms'])}: {query}")
        # Sort by relevance, not date: CrossRef matches documents containing *any*
        # query word, so date-sorted results are just the newest papers that
        # mention "security" or "injection". Recency comes from the date filter.
        params = {
            "query.bibliographic": query,
            "rows": config["max_results"],
            "filter": f"has-abstract:true,from-pub-date:{from_date}",
            "sort": "relevance",
            "order": "desc",
            "select": "DOI,title,author,published-print,published-online,abstract,URL,"
                      "is-referenced-by-count,container-title",
        }
        try:
            items = get_with_retry(config["api_url"], params=params, headers=HEADERS).json()
            batch = parse_items(items.get("message", {}).get("items", []))
            for paper in batch:
                key = paper["doi"] or paper["title"].lower()
                if key not in seen:
                    seen.add(key)
                    papers.append(paper)
            print(f"  {len(batch)} papers ({len(papers)} unique so far)")
        except Exception as exc:  # report, don't crash: other queries still run
            errors.append(f"{query}: {exc}")
            print(f"  Error: {exc}", file=sys.stderr)
        if i < len(config["query_terms"]) - 1:
            time.sleep(2)

    write_candidates(output, "crossref", papers, errors)
    return exit_code(papers, errors)


if __name__ == "__main__":
    sys.exit(main())
