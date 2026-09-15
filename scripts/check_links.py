#!/usr/bin/env python3
"""Find dead links in data/literature.json.

arXiv links are skipped (stable, and the API rate-limits CI runners). DOIs are
checked at doi.org without following the redirect, which says whether the DOI
exists without depending on publisher bot protection. Other links are fetched;
401/403/429-style answers mean "blocked for bots", not "gone", so they are
reported separately instead of as broken.

Writes a Markdown report and exits 0; the workflow decides what to do with it.
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests

from fetch_common import USER_AGENT

ROOT = Path(__file__).resolve().parent.parent
LITERATURE = ROOT / "data" / "literature.json"

SKIP_HOSTS = {"arxiv.org", "www.arxiv.org", "export.arxiv.org"}
UNVERIFIABLE = {401, 403, 405, 406, 429, 999}  # 999: LinkedIn-style bot wall
TIMEOUT = 25


@dataclass
class Result:
    entry_id: str
    title: str
    field: str
    url: str
    status: str  # "ok", "broken" or "unverifiable"
    detail: str


def link_targets(literature: dict) -> list[tuple[dict, str, str]]:
    """(entry, field, url) for every url/pdf_url worth checking."""
    targets = []
    for entry in literature["entries"]:
        for field in ("url", "pdf_url"):
            url = entry.get(field)
            if url and urlparse(url).hostname not in SKIP_HOSTS:
                targets.append((entry, field, url))
    return targets


def classify(status_code: int, is_doi: bool) -> str:
    if is_doi:
        # doi.org answers 30x for registered DOIs and 404 for unknown ones
        return "ok" if 300 <= status_code < 400 or status_code == 200 else "broken"
    if status_code < 400:
        return "ok"
    return "unverifiable" if status_code in UNVERIFIABLE else "broken"


def check(entry: dict, field: str, url: str, session: requests.Session) -> Result:
    is_doi = urlparse(url).hostname in {"doi.org", "dx.doi.org"}
    try:
        response = session.get(url, timeout=TIMEOUT, allow_redirects=not is_doi, stream=True)
        response.close()
        status = classify(response.status_code, is_doi)
        detail = f"HTTP {response.status_code}"
    except requests.exceptions.SSLError as exc:
        status, detail = "unverifiable", f"TLS error: {type(exc).__name__}"
    except requests.exceptions.ConnectionError:
        status, detail = "broken", "connection failed (DNS or refused)"
    except requests.exceptions.Timeout:
        status, detail = "unverifiable", "timed out"
    return Result(entry["id"], entry.get("title", ""), field, url, status, detail)


def run(literature: dict, workers: int = 8) -> list[Result]:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    targets = link_targets(literature)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(lambda t: check(*t, session), targets))


def report(results: list[Result]) -> str:
    broken = [r for r in results if r.status == "broken"]
    unverifiable = [r for r in results if r.status == "unverifiable"]
    lines = [
        f"Checked {len(results)} links (arXiv links skipped): "
        f"**{len(broken)} broken**, {len(unverifiable)} could not be verified.",
    ]
    for heading, group in (("Broken", broken), ("Could not verify (bot protection, timeouts)", unverifiable)):
        if not group:
            continue
        lines += ["", f"### {heading}", "", "| Entry | Field | Link | Result |", "|---|---|---|---|"]
        for r in sorted(group, key=lambda r: r.entry_id):
            title = r.title.replace("|", "\\|")[:80]
            lines.append(f"| `{r.entry_id}` {title} | {r.field} | <{r.url}> | {r.detail} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=Path("link_report.md"))
    args = parser.parse_args()

    results = run(json.loads(LITERATURE.read_text(encoding="utf-8")))
    args.output.write_text(report(results), encoding="utf-8")
    broken = sum(r.status == "broken" for r in results)
    print(f"{len(results)} links checked, {broken} broken; report in {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
