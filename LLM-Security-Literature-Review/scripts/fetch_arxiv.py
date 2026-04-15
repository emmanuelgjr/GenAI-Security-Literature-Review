#!/usr/bin/env python3
"""Fetch new LLM security papers from arXiv API."""

import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_FILE = ROOT / "scripts" / "candidates_arxiv.json"

ARXIV_API = "https://export.arxiv.org/api/query"
CATEGORIES = ["cs.CR", "cs.AI", "cs.CL", "cs.LG"]

QUERIES = [
    '(ti:"large language model" OR ti:LLM) AND (ti:security OR ti:attack OR ti:vulnerability)',
    '(abs:"prompt injection" OR abs:jailbreak) AND cat:cs.CR',
    '(ti:"AI safety" OR ti:"AI security") AND (ti:adversarial OR ti:defense)',
    '(abs:"language model" AND abs:poisoning)',
    '(abs:"AI agent" OR abs:"agentic AI") AND (abs:security OR abs:safety)',
]

MAX_RESULTS_PER_QUERY = 50


def fetch_query(query: str, max_results: int = MAX_RESULTS_PER_QUERY) -> list[dict]:
    """Fetch papers from arXiv for a single query."""
    params = urllib.parse.urlencode({
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    })
    url = f"{ARXIV_API}?{params}"

    req = urllib.request.Request(url, headers={"User-Agent": "LLMSecLitReview/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        xml_data = resp.read()

    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    root = ET.fromstring(xml_data)

    papers = []
    for entry in root.findall("atom:entry", ns):
        title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
        title = re.sub(r"\s+", " ", title)

        abstract = entry.find("atom:summary", ns).text.strip().replace("\n", " ")
        abstract = re.sub(r"\s+", " ", abstract)

        authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)]

        arxiv_id_full = entry.find("atom:id", ns).text.strip()
        arxiv_id = arxiv_id_full.split("/abs/")[-1]
        arxiv_id = re.sub(r"v\d+$", "", arxiv_id)

        published = entry.find("atom:published", ns).text[:10]
        year = int(published[:4])
        month = int(published[5:7])

        pdf_url = ""
        for link in entry.findall("atom:link", ns):
            if link.get("title") == "pdf":
                pdf_url = link.get("href", "")

        categories = []
        for cat in entry.findall("atom:category", ns):
            categories.append(cat.get("term", ""))

        doi_el = entry.find("arxiv:doi", ns)
        doi = doi_el.text.strip() if doi_el is not None else ""

        papers.append({
            "title": title,
            "authors": authors,
            "year": year,
            "month": month,
            "abstract": abstract[:500],
            "url": f"https://arxiv.org/abs/{arxiv_id}",
            "pdf_url": pdf_url or f"https://arxiv.org/pdf/{arxiv_id}",
            "doi": doi,
            "arxiv_id": arxiv_id,
            "arxiv_categories": categories,
        })

    return papers


def main():
    all_papers = []
    seen_ids = set()

    for i, query in enumerate(QUERIES):
        print(f"Query {i+1}/{len(QUERIES)}: {query[:80]}...")
        try:
            papers = fetch_query(query)
            for p in papers:
                if p["arxiv_id"] not in seen_ids:
                    seen_ids.add(p["arxiv_id"])
                    all_papers.append(p)
            print(f"  Found {len(papers)} papers ({len(all_papers)} unique total)")
        except Exception as e:
            print(f"  Error: {e}", file=sys.stderr)

        # arXiv rate limit: 1 request per 3 seconds
        if i < len(QUERIES) - 1:
            time.sleep(3)

    # Filter to recent papers (last 12 months)
    cutoff = datetime.now() - timedelta(days=365)
    cutoff_year = cutoff.year
    cutoff_month = cutoff.month
    recent = [
        p for p in all_papers
        if p["year"] > cutoff_year or (p["year"] == cutoff_year and p["month"] >= cutoff_month)
    ]

    print(f"\n{len(recent)} recent papers (last 12 months) out of {len(all_papers)} total")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({"source": "arxiv", "fetched_at": datetime.now().isoformat(), "papers": recent}, f, indent=2)

    print(f"Written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
