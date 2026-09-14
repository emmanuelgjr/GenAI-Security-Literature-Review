#!/usr/bin/env python3
"""Deduplicate candidate papers against existing literature and merge new entries."""

import argparse
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


def add_to_index(paper: dict, index: dict) -> None:
    """Record a newly accepted paper so later candidates dedup against it."""
    if paper.get("arxiv_id"):
        index["arxiv_ids"].add(paper["arxiv_id"])
    if paper.get("doi"):
        index["dois"].add(paper["doi"].lower())
    if paper.get("semantic_scholar_id"):
        index["s2_ids"].add(paper["semantic_scholar_id"])
    index["titles"].append(normalize_title(paper.get("title", "")))


def entry_lookup_keys(entry: dict) -> dict:
    """Flatten a literature entry into the candidate-paper shape is_duplicate expects."""
    ext = entry.get("external_ids", {})
    return {
        "title": entry.get("title", ""),
        "doi": entry.get("doi") or ext.get("doi", ""),
        "arxiv_id": ext.get("arxiv_id", ""),
        "semantic_scholar_id": ext.get("semantic_scholar_id", ""),
    }


def pending_entries(pending: dict, index: dict) -> list[dict]:
    """Entries from the open auto-fetch PR that main does not have yet.

    The weekly run rebuilds that PR from main, so without this anything found in
    an earlier week and not yet merged would silently drop off the PR. Entries
    are kept verbatim (a reviewer may have fixed categories on the branch); only
    their IDs are reassigned by the caller.
    """
    kept = []
    for entry in pending.get("entries", []):
        keys = entry_lookup_keys(entry)
        if is_duplicate(keys, index):
            continue
        add_to_index(keys, index)
        kept.append(dict(entry))
    return kept


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


CATEGORY_KEYWORDS = {
    # Attacks & Threats
    "prompt-injection": ["prompt injection", "prompt-injection", "indirect injection", "confused deputy"],
    "jailbreaking": ["jailbreak", "jailbreaking", "safety bypass"],
    "data-poisoning": ["data poisoning", "training data poison", "poisoning", "backdoor", "trojan"],
    "model-extraction": ["model extraction", "model stealing", "model theft", "prompt stealing"],
    "membership-inference": ["membership inference", "training data extraction", "extracting training data",
                             "extraction of training data", "training data detection", "data leakage",
                             "privacy leakage", "privacy risk", "sensitive information"],
    "adversarial-examples": ["adversarial example", "adversarial attack", "adversarial perturbation", "evasion attack"],
    "supply-chain-attacks": ["supply chain", "model repository", "dependency attack"],
    "social-engineering": ["deepfake", "ai-generated phishing", "voice cloning", "synthetic media"],
    "agentic-threats": ["agent attack", "agentic", "tool misuse", "agent security", "llm agent"],

    # Defenses & Mitigations
    "input-filtering": ["input filter", "input validation", "prompt filter"],
    "output-moderation": ["output filter", "content filter", "output moderation"],
    "guardrails": ["guardrail", "safeguard", "safety boundar", "safety training", "constitutional ai", "alignment"],
    "access-control": ["access control", "authorization", "rbac", "abac"],
    "monitoring-detection": ["anomaly detection", "monitoring", "drift detection"],
    "sandboxing-isolation": ["sandbox", "sandboxing", "execution containment", "tool sandbox"],
    "cryptographic-controls": ["homomorphic encryption", "secure multi-party computation", "model signing"],
    "watermarking": ["watermark"],

    # Privacy
    "differential-privacy": ["differential privacy", "dp-sgd"],
    "federated-learning": ["federated learning", "federated fine-tuning"],
    "data-anonymization": ["data anonymization", "pii removal", "de-identification", "synthetic data generation"],
    "unlearning": ["machine unlearning", "model unlearning"],
    "confidential-computing": ["confidential computing", "trusted execution environment", "secure enclave", "tee inference"],

    # Governance & Compliance
    "risk-frameworks": ["nist ai rmf", "iso 42001", "eu ai act", "ai risk management framework"],
    "model-governance": ["model card", "model governance", "model lifecycle", "datasheet for datasets"],
    "audit-assurance": ["ai audit", "ai assurance", "algorithmic audit"],
    "responsible-ai": ["responsible ai", "trustworthy ai", "ai ethics"],
    "incident-response": ["ai incident", "ai forensics", "ai security playbook"],

    # Red Teaming & Evaluation
    "red-teaming": ["red team", "red-team"],
    "benchmarks": ["benchmark", "evaluation framework"],
    "fuzzing": ["llm fuzzing", "prompt fuzzing", "fuzz testing"],
    "vulnerability-disclosure": ["vulnerability disclosure", "coordinated disclosure", "cve assignment"],

    # Infrastructure & Deployment
    "model-serving-security": ["model serving security", "inference endpoint security", "inference api security"],
    "rag-security": ["rag security", "retrieval augmented", "vector database attack"],
    "fine-tuning-security": ["fine-tuning security", "fine-tuning attack", "lora attack"],
    "mlops-security": ["mlops security", "ml pipeline security", "model artifact security"],
    "cloud-ai-security": ["managed ai service", "multi-tenant ai", "cloud ai security", "security posture management"],

    # Agentic AI Security
    "agent-architecture": ["multi-agent", "agent architecture"],
    "tool-use-security": ["tool use", "function calling", "plugin security"],
    "memory-security": ["memory poisoning", "long-term memory attack", "context window attack"],
    "human-in-the-loop": ["human-in-the-loop", "human oversight", "human approval"],
    "autonomous-operations": ["autonomous agent", "self-modifying agent", "agent containment"],

    # Surveys & Meta
    "survey": ["survey of", "survey on", "systematic review", "systematization of knowledge", "literature review"],
    "threat-modeling": ["threat model", "threat modeling", "attack taxonomy", "kill chain", "security risk", "risk assessment"],
}

_CATEGORY_PATTERNS = {
    category: re.compile(
        r"(?<![a-z0-9])(?:" + "|".join(re.escape(k) for k in keywords) + ")"
    )
    for category, keywords in CATEGORY_KEYWORDS.items()
}


# A candidate must be about generative AI / LLMs *and* about security. Either
# signal alone is not enough: CrossRef matches any query word, so "injection"
# brings in medical trials and "supply chain" brings in agri-food reviews, while
# plenty of LLM papers (scheduling, education, construction) have no security angle.
GENAI_RE = re.compile(
    r"(?<![a-z0-9])(?:"
    r"large language models?|llms?|language models?|gen ?ai|generative ai"
    r"|generative artificial intelligence|foundation models?|frontier (?:ai|models?)"
    r"|gpts?|chatgpt|chatbots?|copilots?|llama|gemini|claude|mistral|qwen|deepseek"
    r"|ai agents?|llm agents?|agentic|adversarial (?:machine learning|ml|ai)"
    r"|(?:web|browser|coding|gui|computer-us(?:e|ing)|mobile|multimodal|terminal|tool-using) agents?"
    r"|vision-language|vlms?|mllms?|lvlms?|multimodal (?:large )?models?"
    r"|diffusion models?|text-to-image|retrieval-augmented|rag"
    r"|model context protocol|mcp|prompt[- ]injection|jailbreak\w*|deepfakes?"
    r"|ai (?:models?|systems?|applications?|assistants?|workloads?|supply chains?"
    r"|safety|security|control|red[- ]?team\w*)"
    r")(?![a-z0-9])"
)
SECURITY_RE = re.compile(
    r"(?<![a-z0-9])(?:"
    r"(?:cyber)?secur\w*|attack\w*|adversar\w*|jailbreak\w*|prompt[- ]injection"
    r"|injection attacks?|hijack\w*|decepti\w*|misalign\w*|anomal\w*"
    r"|indirect injection|poison\w*|backdoor\w*|trojan\w*|vulnerab\w*|threats?"
    r"|exploit\w*|malicious\w*|privacy|leak\w*|red[- ]?team\w*|guardrails?"
    r"|safeguard\w*|safety|unsafe|harmful|misuse|abuse|defen[cs]es?|defend\w*"
    r"|watermark\w*|membership inference|unlearning|model (?:stealing|extraction)"
    r"|authori[sz]\w*|authenticat\w*|access control|permissions?|sandbox\w*"
    r"|phishing|deepfakes?|fraud|evasion|tamper\w*|trustworth\w*|governance"
    r"|audit\w*|risk management|ai act"
    r")(?![a-z0-9])"
)


def is_on_topic(paper: dict) -> bool:
    """Accept only candidates that are about GenAI/LLMs, security, and a taxonomy topic."""
    text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
    return bool(
        GENAI_RE.search(text)
        and SECURITY_RE.search(text)
        and auto_categorize(text)
    )


def auto_categorize(text: str) -> list[str]:
    """Simple keyword-based auto-categorization.

    Covers all topic-bearing taxonomy categories. The three resource-type
    categories (book, industry-report, conference-proceedings) are intentionally
    excluded -- the upstream sources (arXiv, Semantic Scholar, CrossRef) only
    return papers, so those would never match anyway.
    """
    # Match at word starts so "shared team" does not count as "red team";
    # suffixes stay open so plurals still match.
    return [
        category
        for category, pattern in _CATEGORY_PATTERNS.items()
        if pattern.search(text)
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pending",
        type=Path,
        help="literature.json from the open auto-fetch PR branch; its unmerged entries are carried over",
    )
    args = parser.parse_args()

    # Load existing literature
    lit_path = DATA_DIR / "literature.json"
    with open(lit_path, encoding="utf-8") as f:
        literature = json.load(f)

    index = build_existing_index(literature)
    next_num = get_next_id(literature)
    year = datetime.now().year

    new_entries = []
    seen_in_candidates = set()

    if args.pending and args.pending.exists():
        with open(args.pending, encoding="utf-8") as f:
            carried = pending_entries(json.load(f), index)
        for entry in carried:
            entry["id"] = f"llmsec-{year}-{next_num:05d}"
            next_num += 1
            seen_in_candidates.add(normalize_title(entry["title"]))
        new_entries.extend(carried)
        print(f"Carried over {len(carried)} unmerged entries from {args.pending.name}")

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

            # Drop candidates that are not about GenAI security (see is_on_topic)
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
            add_to_index(paper, index)

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
