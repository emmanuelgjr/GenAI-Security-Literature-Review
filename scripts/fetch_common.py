#!/usr/bin/env python3
"""Shared plumbing for the fetch_*.py scripts: config, HTTP retries, candidate files.

Run directly with --report to summarise the candidate files a fetch run left
behind (as Markdown) and exit non-zero if no enabled source produced anything.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
SOURCES_FILE = ROOT / "data" / "sources.json"
SCRIPTS_DIR = ROOT / "scripts"

USER_AGENT = "LLMSecLitReview/1.0 (+https://github.com/emmanuelgjr/GenAI-Security-Literature-Review)"
RETRY_STATUSES = {429, 500, 502, 503, 504}
MAX_RETRY_WAIT = 120.0


def load_source(source_id: str, path: Path = SOURCES_FILE) -> dict:
    """Return the config block for one source from data/sources.json."""
    sources = json.loads(path.read_text(encoding="utf-8"))["sources"]
    for source in sources:
        if source["id"] == source_id:
            return source
    raise KeyError(f"source {source_id!r} not found in {path.name}")


def retry_delay(response: requests.Response | None, attempt: int, backoff: float) -> float:
    """Seconds to wait before retry number `attempt` (0-based).

    Honours a numeric Retry-After header; otherwise exponential backoff with a
    little jitter so parallel runs don't retry in lockstep.
    """
    if response is not None:
        retry_after = response.headers.get("Retry-After", "")
        if retry_after.isdigit():
            return min(float(retry_after), MAX_RETRY_WAIT)
    return min(backoff * (2 ** attempt) + random.uniform(0, 1), MAX_RETRY_WAIT)


def get_with_retry(
    url: str,
    *,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: float = 60,
    attempts: int = 4,
    backoff: float = 10.0,
    sleep=time.sleep,
) -> requests.Response:
    """GET with retries on rate limiting, server errors, timeouts and dropped connections.

    arXiv and Semantic Scholar both answer bursts from shared CI runners with
    429s; without retries a whole source silently returns nothing.
    """
    merged_headers = {"User-Agent": USER_AGENT, **(headers or {})}
    last_error: Exception | None = None
    for attempt in range(attempts):
        response = None
        try:
            response = requests.get(url, params=params, headers=merged_headers, timeout=timeout)
            if response.status_code not in RETRY_STATUSES:
                response.raise_for_status()
                return response
            last_error = requests.HTTPError(f"HTTP {response.status_code} from {url}", response=response)
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_error = exc
        if attempt < attempts - 1:
            wait = retry_delay(response, attempt, backoff)
            print(f"  {last_error}; retrying in {wait:.0f}s", file=sys.stderr)
            sleep(wait)
    assert last_error is not None
    raise last_error


def write_candidates(path: Path, source: str, papers: list[dict], errors: list[str]) -> None:
    """Write a candidates file, including errors so the run report can surface them."""
    payload = {
        "source": source,
        "fetched_at": datetime.now().isoformat(),
        "errors": errors,
        "papers": papers,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(papers)} papers to {path.name}" + (f" ({len(errors)} errors)" if errors else ""))


def exit_code(papers: list[dict], errors: list[str]) -> int:
    """Non-zero when a source failed outright, so the workflow step is flagged."""
    return 1 if errors and not papers else 0


def report(scripts_dir: Path = SCRIPTS_DIR, sources_file: Path = SOURCES_FILE) -> tuple[str, bool]:
    """Markdown health table for the latest fetch, and whether any source delivered."""
    sources = json.loads(sources_file.read_text(encoding="utf-8"))["sources"]
    rows = ["| Source | Candidates | Status |", "|---|---|---|"]
    any_ok = False
    for source in sources:
        if not source.get("enabled", True):
            rows.append(f"| {source['name']} | - | disabled |")
            continue
        path = scripts_dir / source["candidates_file"]
        if not path.exists():
            rows.append(f"| {source['name']} | 0 | :x: no output (script crashed?) |")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        count, errors = len(data.get("papers", [])), data.get("errors", [])
        if errors and not count:
            status = f":x: failed: {errors[0]}"
        elif errors:
            status = f":warning: partial ({len(errors)} errors)"
        else:
            status = ":white_check_mark: ok"
        any_ok = any_ok or count > 0 or not errors
        rows.append(f"| {source['name']} | {count} | {status} |")
    return "\n".join(rows), any_ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="store_true", help="print the source health table")
    args = parser.parse_args()
    if not args.report:
        parser.print_help()
        return 2
    table, any_ok = report()
    print(table)
    return 0 if any_ok else 1


if __name__ == "__main__":
    sys.exit(main())
