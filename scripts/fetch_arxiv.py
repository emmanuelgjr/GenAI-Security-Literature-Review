#!/usr/bin/env python3
"""Fetch new papers from arXiv via OAI-PMH (sets and window in data/sources.json).

The arXiv search API (export.arxiv.org/api/query) answers GitHub-hosted runners
with HTTP 429 even for a single request, so this harvests whole categories from
the OAI-PMH endpoint instead and leaves relevance to deduplicate.is_on_topic.
"""

from __future__ import annotations

import re
import sys
import time
from datetime import datetime, timedelta
from xml.etree.ElementTree import Element

from defusedxml import ElementTree as ET

from fetch_common import SCRIPTS_DIR, exit_code, get_with_retry, load_source, write_candidates

NS = {"oai": "http://www.openarchives.org/OAI/2.0/", "arxiv": "http://arxiv.org/OAI/arXiv/"}
MAX_PAGES_PER_SET = 20
PAGE_DELAY_SECONDS = 5  # arXiv asks harvesters to pace resumption requests


def _text(node: Element | None, path: str) -> str:
    found = node.find(path, NS) if node is not None else None
    return re.sub(r"\s+", " ", found.text or "").strip() if found is not None else ""


def submission_month(arxiv_id: str) -> tuple[int, int] | None:
    """(year, month) of first submission, read from the identifier.

    OAI datestamps and <created> move when a paper is revised, so a 2022 paper
    with a new version would otherwise look brand new.
    """
    match = re.match(r"^(\d{2})(\d{2})\.\d{4,5}$", arxiv_id) or re.search(r"/(\d{2})(\d{2})\d{3}$", arxiv_id)
    if not match:
        return None
    yy, mm = int(match.group(1)), int(match.group(2))
    return (2000 + yy if yy < 90 else 1900 + yy), mm


def parse_records(xml_data: bytes) -> tuple[list[dict], str | None]:
    """Parse a ListRecords page (or a GetRecord response) into papers and the resumption token."""
    root = ET.fromstring(xml_data)
    error = root.find("oai:error", NS)
    if error is not None:
        if error.get("code") == "noRecordsMatch":
            return [], None
        raise ValueError(f"OAI-PMH error {error.get('code')}: {(error.text or '').strip()}")

    papers = []
    for record in root.iterfind("./*/oai:record", NS):  # ListRecords or GetRecord
        header = record.find("oai:header", NS)
        meta = record.find("oai:metadata/arxiv:arXiv", NS)
        if meta is None or (header is not None and header.get("status") == "deleted"):
            continue
        arxiv_id = _text(meta, "arxiv:id")
        year, month = submission_month(arxiv_id) or (0, 0)
        authors = [
            " ".join(filter(None, [_text(a, "arxiv:forenames"), _text(a, "arxiv:keyname")]))
            for a in meta.iterfind("arxiv:authors/arxiv:author", NS)
        ]
        papers.append({
            "title": _text(meta, "arxiv:title"),
            "authors": [a for a in authors if a],
            "year": year,
            "month": month,
            "abstract": _text(meta, "arxiv:abstract")[:500],
            "url": f"https://arxiv.org/abs/{arxiv_id}",
            "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}",
            "doi": _text(meta, "arxiv:doi"),
            "arxiv_id": arxiv_id,
            "arxiv_categories": _text(meta, "arxiv:categories").split(),
        })
    token = _text(root, "oai:ListRecords/oai:resumptionToken") or None
    return papers, token


def harvest_set(api_url: str, set_spec: str, since: str, sleep=time.sleep) -> list[dict]:
    """All records in one OAI set changed since `since`, following resumption tokens."""
    params = {"verb": "ListRecords", "metadataPrefix": "arXiv", "set": set_spec, "from": since}
    papers: list[dict] = []
    for page in range(MAX_PAGES_PER_SET):
        # OAI-PMH flow control answers 503 + Retry-After; get_with_retry honours it
        response = get_with_retry(api_url, params=params, timeout=180, attempts=5, backoff=30)
        batch, token = parse_records(response.content)
        papers.extend(batch)
        print(f"  {set_spec} page {page + 1}: {len(batch)} records")
        if not token:
            break
        params = {"verb": "ListRecords", "resumptionToken": token}
        sleep(PAGE_DELAY_SECONDS)
    return papers


def main() -> int:
    config = load_source("arxiv")
    output = SCRIPTS_DIR / config["candidates_file"]
    if not config.get("enabled", True):
        print("arXiv source disabled in sources.json")
        return 0

    since_date = datetime.now() - timedelta(days=config["lookback_days"])
    since = since_date.strftime("%Y-%m-%d")
    papers, errors, seen = [], [], set()
    for set_spec in config["oai_sets"]:
        try:
            for paper in harvest_set(config["api_url"], set_spec, since):
                if paper["arxiv_id"] not in seen:
                    seen.add(paper["arxiv_id"])
                    papers.append(paper)
        except Exception as exc:  # report, don't crash: other sets and sources still run
            errors.append(f"{set_spec}: {exc}")
            print(f"Error harvesting {set_spec}: {exc}", file=sys.stderr)

    cutoff = (since_date.year, since_date.month)
    recent = [p for p in papers if (p["year"], p["month"]) >= cutoff]
    print(f"{len(recent)} papers first submitted since {cutoff[0]}-{cutoff[1]:02d} "
          f"(of {len(papers)} records updated since {since})")

    write_candidates(output, "arxiv", recent, errors)
    return exit_code(recent, errors)


if __name__ == "__main__":
    sys.exit(main())
