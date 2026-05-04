#!/usr/bin/env python3
"""Deduplicate candidate papers against existing literature and merge new entries."""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SCRIPTS_DIR = ROOT / "scripts"

CANDIDATE_FILES = [
    SCRIPTS_DIR / "candidates_arxiv.json",
    SCRIPTS_DIR / "candidates_s2.json",
    SCRIPTS_DIR / "candidates_crossref.json",
]


def normalize_title(title: str) -> str:
    """Normalize title for comparison."""
    title = title.lower().strip()
    title = re.sub(r"[^a-z0-9\s]", "", title)
    title = re.sub(r"\s+", " ", title)
    return title


def title_similarity(a: str, b: str) -> float:
    """Simple Jaccard similarity between title word sets."""
    words_a = set(normalize_title(a).split())
    words_b = set(normalize_title(b).split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def build_existing_index(literature: dict) -> dict:
    """Build lookup indices from existing literature."""
    index = {
        "arxiv_ids": set(),
        "dois": set(),
        "s2_ids": set(),
        "titles": [],
    }
    for entry in literature["entries"]:
        ext = entry.get("external_ids", {})
        if ext.get("arxiv_id"):
            index["arxiv_ids"].add(ext["arxiv_id"])
        if ext.get("doi"):
            index["dois"].add(ext["doi"].lower())
        if ext.get("semantic_scholar_id"):
            index["s2_ids"].add(ext["semantic_scholar_id"])
        if entry.get("doi"):
            index["dois"].add(entry["doi"].lower())
        index["titles"].append(normalize_title(entry["title"]))
    return index


def is_duplicate(paper: dict, index: dict) -> bool:
    """Check if a paper is a duplicate of an existing entry."""
    # Check arXiv ID
    if paper.get("arxiv_id") and paper["arxiv_id"] in index["arxiv_ids"]:
        return True

    # Check DOI
    if paper.get("doi") and paper["doi"].lower() in index["dois"]:
        return True

    # Check Semantic Scholar ID
    if paper.get("semantic_scholar_id") and paper["semantic_scholar_id"] in index["s2_ids"]:
        return True

    # Check title similarity
    norm_title = normalize_title(paper.get("title", ""))
    for existing_title in index["titles"]:
        if title_similarity(norm_title, existing_title) > 0.85:
            return True

    return False


def get_next_id(literature: dict) -> int:
    """Get the next sequential ID number."""
    max_num = 0
    for entry in literature["entries"]:
        match = re.search(r"-(\d{5})$", entry["id"])
        if match:
            max_num = max(max_num, int(match.group(1)))
    return max_num + 1


YEAR_MIN = 2017
YEAR_MAX = datetime.now().year + 1


def is_valid_candidate(paper: dict) -> tuple[bool, str]:
    """Reject candidates that would fail schema validation."""
    year = paper.get("year")
    if not isinstance(year, int) or year < YEAR_MIN or year > YEAR_MAX:
        return False, f"year={year!r} outside [{YEAR_MIN},{YEAR_MAX}]"
    authors = paper.get("authors") or []
    if not authors:
        return False, "empty authors"
    title = (paper.get("title") or "").strip()
    if not title:
        return False, "empty title"
    url = (paper.get("url") or "").strip()
    if not url:
        return False, "empty url"
    return True, ""


def paper_to_entry(paper: dict, entry_id: str, source: str) -> dict:
    """Convert a candidate paper to a literature entry."""
    entry = {
        "id": entry_id,
        "type": "paper",
        "title": paper["title"],
        "authors": paper.get("authors", []),
        "year": paper.get("year", 0),
        "url": paper.get("url", ""),
        "categories": [],
        "added_date": datetime.now().strftime("%Y-%m-%d"),
        "added_by": "automation",
        "source_api": source,
        "external_ids": {},
        "reviewed": False,
    }

    if paper.get("month"):
        entry["month"] = paper["month"]
    if paper.get("venue"):
        entry["venue"] = paper["venue"]
    if paper.get("abstract"):
        entry["abstract"] = paper["abstract"]
    if paper.get("doi"):
        entry["doi"] = paper["doi"]
        entry["external_ids"]["doi"] = paper["doi"]
    if paper.get("pdf_url"):
        entry["pdf_url"] = paper["pdf_url"]
    if paper.get("arxiv_id"):
        entry["external_ids"]["arxiv_id"] = paper["arxiv_id"]
    if paper.get("semantic_scholar_id"):
        entry["external_ids"]["semantic_scholar_id"] = paper["semantic_scholar_id"]
    if paper.get("citation_count"):
        entry["citation_count"] = paper["citation_count"]
    if paper.get("open_access") is not None:
        entry["open_access"] = paper["open_access"]

    # Auto-categorize based on title/abstract keywords
    text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
    categories = auto_categorize(text)
    entry["categories"] = categories

    return entry


def is_on_topic(paper: dict) -> bool:
    """Reject papers whose title/abstract don't match any taxonomy keyword.

    Without this, broad CrossRef queries pull in unrelated medical/education/
    sustainability papers that would get bucketed into 'survey' by default.
    """
    text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
    return bool(auto_categorize(text))


def auto_categorize(text: str) -> list[str]:
    """Simple keyword-based auto-categorization."""
    categories = []
    keyword_map = {
        "prompt-injection": ["prompt injection", "indirect injection"],
        "jailbreaking": ["jailbreak", "jailbreaking", "safety bypass"],
        "data-poisoning": ["data poisoning", "training data poison", "backdoor attack"],
        "model-extraction": ["model extraction", "model stealing", "model theft"],
        "membership-inference": ["membership inference", "training data extraction", "data leakage"],
        "adversarial-examples": ["adversarial example", "adversarial attack", "adversarial perturbation", "evasion attack"],
        "supply-chain-attacks": ["supply chain", "model repository", "dependency attack"],
        "agentic-threats": ["agent attack", "agentic", "tool misuse", "agent security"],
        "input-filtering": ["input filter", "input validation", "prompt filter"],
        "output-moderation": ["output filter", "content filter", "output moderation"],
        "guardrails": ["guardrail", "safety training", "constitutional ai", "alignment"],
        "access-control": ["access control", "authorization", "rbac", "abac"],
        "monitoring-detection": ["anomaly detection", "monitoring", "drift detection"],
        "watermarking": ["watermark"],
        "differential-privacy": ["differential privacy", "dp-sgd"],
        "federated-learning": ["federated learning", "federated fine-tuning"],
        "unlearning": ["machine unlearning", "model unlearning"],
        "red-teaming": ["red team", "red-team"],
        "benchmarks": ["benchmark", "evaluation framework"],
        "rag-security": ["rag security", "retrieval augmented", "vector database attack"],
        "fine-tuning-security": ["fine-tuning security", "fine-tuning attack", "lora attack"],
        "tool-use-security": ["tool use", "function calling", "plugin security"],
        "agent-architecture": ["multi-agent", "agent architecture"],
    }

    for category, keywords in keyword_map.items():
        for keyword in keywords:
            if keyword in text:
                categories.append(category)
                break

    return list(dict.fromkeys(categories))  # dedupe preserving order


def main():
    # Load existing literature
    lit_path = DATA_DIR / "literature.json"
    with open(lit_path, encoding="utf-8") as f:
        literature = json.load(f)

    index = build_existing_index(literature)
    next_num = get_next_id(literature)
    year = datetime.now().year

    new_entries = []
    seen_in_candidates = set()

    for cand_file in CANDIDATE_FILES:
        if not cand_file.exists():
            print(f"Skipping {cand_file.name} (not found)")
            continue

        with open(cand_file, encoding="utf-8") as f:
            candidates = json.load(f)

        source = candidates.get("source", "manual")
        papers = candidates.get("papers", [])
        print(f"\nProcessing {cand_file.name}: {len(papers)} candidates from {source}")

        added = 0
        skipped_invalid = 0
        skipped_offtopic = 0
        for paper in papers:
            # Drop candidates that would fail schema validation
            ok, reason = is_valid_candidate(paper)
            if not ok:
                skipped_invalid += 1
                continue

            # Drop candidates with no taxonomy-keyword match (off-topic)
            if not is_on_topic(paper):
                skipped_offtopic += 1
                continue

            # Check against existing
            if is_duplicate(paper, index):
                continue

            # Check against other candidates in this batch
            norm = normalize_title(paper.get("title", ""))
            if norm in seen_in_candidates:
                continue
            seen_in_candidates.add(norm)

            entry_id = f"llmsec-{year}-{next_num:05d}"
            entry = paper_to_entry(paper, entry_id, source)
            new_entries.append(entry)
            next_num += 1
            added += 1

            # Update index for subsequent dedup
            if paper.get("arxiv_id"):
                index["arxiv_ids"].add(paper["arxiv_id"])
            if paper.get("doi"):
                index["dois"].add(paper["doi"].lower())
            index["titles"].append(norm)

        print(f"  Added {added} new entries (skipped {skipped_invalid} invalid, {skipped_offtopic} off-topic)")

    if not new_entries:
        print("\nNo new entries to add.")
        sys.exit(0)

    # Merge into literature
    literature["entries"].extend(new_entries)

    with open(lit_path, "w", encoding="utf-8") as f:
        json.dump(literature, f, indent=2, ensure_ascii=False)

    print(f"\nAdded {len(new_entries)} new entries. Total: {len(literature['entries'])}")

    # Print summary for PR description
    print("\n--- New Entries ---")
    for entry in new_entries:
        print(f"- [{entry['id']}] {entry['title']}")
        print(f"  {entry['url']}")
        print(f"  Categories: {', '.join(entry['categories'])}")


if __name__ == "__main__":
    main()
