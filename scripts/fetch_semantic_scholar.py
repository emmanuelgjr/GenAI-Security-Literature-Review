#!/usr/bin/env python3
"""Fetch new LLM security papers from Semantic Scholar API."""

import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_FILE = ROOT / "scripts" / "candidates_s2.json"

S2_API = "https://api.semanticscholar.org/graph/v1/paper/search"
S2_FIELDS = "paperId,title,authors,year,abstract,url,externalIds,citationCount,isOpenAccess,venue,publicationDate"

QUERIES = [
    "LLM security attack defense",
    "large language model vulnerability prompt injection",
    "AI agent security agentic",
    "LLM jailbreak adversarial",
    "language model privacy data leakage",
    "RAG retrieval augmented generation security",
    "AI red teaming evaluation safety",
]

MAX_RESULTS_PER_QUERY = 50


def fetch_query(query: str, max_results: int = MAX_RESULTS_PER_QUERY) -> list[dict]:
    """Fetch papers from Semantic Scholar for a single query."""
    params = {
        "query": query,
        "limit": max_results,
        "fields": S2_FIELDS,
        "fieldsOfStudy": "Computer Science",
    }
    headers = {"User-Agent": "LLMSecLitReview/1.0"}

    resp = requests.get(S2_API, params=params, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    papers = []
    for item in data.get("data", []):
        if not item.get("title"):
            continue

        authors = [a.get("name", "") for a in (item.get("authors") or []) if a.get("name")]

        ext_ids = item.get("externalIds") or {}
        arxiv_id = ext_ids.get("ArXiv", "")
        doi = ext_ids.get("DOI", "")

        pub_date = item.get("publicationDate", "")
        year = item.get("year") or 0
        month = 0
        if pub_date and len(pub_date) >= 7:
            try:
                month = int(pub_date[5:7])
            except ValueError:
                pass

        abstract = (item.get("abstract") or "")[:500]

        papers.append({
            "title": item["title"],
            "authors": authors,
            "year": year,
            "month": month,
            "abstract": abstract,
            "url": item.get("url", ""),
            "doi": doi,
            "arxiv_id": arxiv_id,
            "semantic_scholar_id": item.get("paperId", ""),
            "citation_count": item.get("citationCount", 0),
            "open_access": item.get("isOpenAccess", False),
            "venue": item.get("venue", ""),
        })

    return papers


def main():
    all_papers = []
    seen_ids = set()

    for i, query in enumerate(QUERIES):
        print(f"Query {i+1}/{len(QUERIES)}: {query}...")
        try:
            papers = fetch_query(query)
            for p in papers:
                key = p["semantic_scholar_id"] or p["doi"] or p["title"].lower()
                if key not in seen_ids:
                    seen_ids.add(key)
                    all_papers.append(p)
            print(f"  Found {len(papers)} papers ({len(all_papers)} unique total)")
        except Exception as e:
            print(f"  Error: {e}", file=sys.stderr)

        # S2 rate limit: 100 requests per 5 minutes
        if i < len(QUERIES) - 1:
            time.sleep(3)

    # Filter: recent papers, and older ones need citations
    cutoff = datetime.now() - timedelta(days=180)
    cutoff_year = cutoff.year
    cutoff_month = cutoff.month

    filtered = []
    for p in all_papers:
        if not p["year"]:
            continue
        is_recent = p["year"] > cutoff_year or (p["year"] == cutoff_year and p["month"] >= cutoff_month)
        if is_recent or p.get("citation_count", 0) >= 3:
            filtered.append(p)

    print(f"\n{len(filtered)} papers after filtering (from {len(all_papers)} unique)")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({"source": "semantic-scholar", "fetched_at": datetime.now().isoformat(), "papers": filtered}, f, indent=2)

    print(f"Written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
