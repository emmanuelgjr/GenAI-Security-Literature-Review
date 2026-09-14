#!/usr/bin/env python3
"""Fetch new LLM security papers from the Semantic Scholar bulk search API.

Uses /paper/search/bulk with a boolean query from data/sources.json and a
publication-date window: one request returns up to 1000 papers, whereas the
relevance search needed one request per query and was rate-limited (429) on
every query of every run from shared CI runners. Set SEMANTIC_SCHOLAR_API_KEY
for a dedicated rate limit.
"""

import os
import sys
import time
from datetime import datetime, timedelta

from fetch_common import SCRIPTS_DIR, exit_code, get_with_retry, load_source, write_candidates

S2_FIELDS = "paperId,title,authors,year,abstract,url,externalIds,citationCount,isOpenAccess,venue,publicationDate"


def parse_items(items: list[dict]) -> list[dict]:
    """Turn Semantic Scholar paper records into candidate papers."""
    papers = []
    for item in items:
        if not item.get("title"):
            continue
        ext_ids = item.get("externalIds") or {}
        pub_date = item.get("publicationDate") or ""
        month = int(pub_date[5:7]) if len(pub_date) >= 7 and pub_date[5:7].isdigit() else 0
        papers.append({
            "title": item["title"],
            "authors": [a["name"] for a in (item.get("authors") or []) if a.get("name")],
            "year": item.get("year") or 0,
            "month": month,
            "abstract": (item.get("abstract") or "")[:500],
            "url": item.get("url", ""),
            "doi": ext_ids.get("DOI", ""),
            "arxiv_id": ext_ids.get("ArXiv", ""),
            "semantic_scholar_id": item.get("paperId", ""),
            "citation_count": item.get("citationCount", 0),
            "open_access": item.get("isOpenAccess", False),
            "venue": item.get("venue", ""),
        })
    return papers


def main() -> int:
    config = load_source("semantic-scholar")
    output = SCRIPTS_DIR / config["candidates_file"]
    if not config.get("enabled", True):
        print("Semantic Scholar source disabled in sources.json")
        return 0

    headers = {}
    if os.environ.get("SEMANTIC_SCHOLAR_API_KEY"):
        headers["x-api-key"] = os.environ["SEMANTIC_SCHOLAR_API_KEY"]
    else:
        print("SEMANTIC_SCHOLAR_API_KEY not set; using the shared unauthenticated rate limit")

    since = (datetime.now() - timedelta(days=config["lookback_days"])).strftime("%Y-%m-%d")
    papers, errors = [], []
    for query in config["query_terms"]:
        params = {
            "query": query,
            "fields": S2_FIELDS,
            "publicationDateOrYear": f"{since}:",
            "sort": "publicationDate:desc",
        }
        token = None
        try:
            while True:
                if token:
                    params["token"] = token
                data = get_with_retry(
                    config["api_url"], params=params, headers=headers, attempts=6, backoff=20
                ).json()
                papers.extend(parse_items(data.get("data") or []))
                token = data.get("token")
                print(f"  {len(papers)} papers so far (total matching: {data.get('total')})")
                if not token or len(papers) >= config["max_results"]:
                    break
                time.sleep(1.5)  # keyed limit is 1 request/second
        except Exception as exc:  # report, don't crash: other sources still run
            errors.append(str(exc))
            print(f"Error: {exc}", file=sys.stderr)

    seen, unique = set(), []
    for paper in papers[: config["max_results"]]:
        key = paper["semantic_scholar_id"] or paper["title"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(paper)
    print(f"{len(unique)} unique papers published since {since}")

    write_candidates(output, "semantic-scholar", unique, errors)
    return exit_code(unique, errors)


if __name__ == "__main__":
    sys.exit(main())
