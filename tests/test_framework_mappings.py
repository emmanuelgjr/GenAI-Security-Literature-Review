"""Tests for scripts/framework_mappings.py and its use in deduplicate.py."""

from deduplicate import paper_to_entry
from framework_mappings import backfill, category_mappings, fill_missing, suggest

TAXONOMY = {"domains": [{"id": "attacks", "label": "Attacks", "categories": [
    {"id": "prompt-injection", "label": "PI",
     "framework_mappings": {"owasp_llm_top10": ["LLM01"], "mitre_atlas": ["AML.T0051"]}},
    {"id": "jailbreaking", "label": "JB",
     "framework_mappings": {"owasp_llm_top10": ["LLM01"], "mitre_atlas": ["AML.T0054"]}},
    {"id": "survey", "label": "Survey"},
]}]}
MAPPINGS = category_mappings(TAXONOMY)


def test_category_mappings_skips_categories_without_mappings():
    assert set(MAPPINGS) == {"prompt-injection", "jailbreaking"}


def test_suggest_unions_and_dedupes_across_categories():
    assert suggest(["prompt-injection", "jailbreaking", "survey"], MAPPINGS) == {
        "mitre_atlas": ["AML.T0051", "AML.T0054"],
        "owasp_llm_top10": ["LLM01"],
    }


def test_suggest_returns_empty_for_unmapped_categories():
    assert suggest(["survey"], MAPPINGS) == {}


def test_fill_missing_never_overwrites_existing_mappings():
    curated = {"categories": ["jailbreaking"], "framework_mappings": {"owasp_llm_top10": ["LLM02"]}}
    assert not fill_missing(curated, MAPPINGS)
    assert curated["framework_mappings"] == {"owasp_llm_top10": ["LLM02"]}


def test_fill_missing_leaves_unmappable_entries_without_the_key():
    entry = {"categories": ["survey"]}
    assert not fill_missing(entry, MAPPINGS)
    assert "framework_mappings" not in entry


def test_backfill_only_touches_unreviewed_automated_entries():
    literature = {"entries": [
        {"id": "a", "categories": ["jailbreaking"], "added_by": "automation", "reviewed": False},
        {"id": "b", "categories": ["jailbreaking"], "added_by": "automation", "reviewed": True},
        {"id": "c", "categories": ["jailbreaking"], "added_by": "manual", "reviewed": False},
    ]}
    assert backfill(literature, TAXONOMY) == 1
    assert [bool(e.get("framework_mappings")) for e in literature["entries"]] == [True, False, False]


def test_paper_to_entry_adds_suggested_mappings():
    paper = {"title": "Jailbreaking aligned LLMs", "authors": ["X"], "year": 2026, "url": "https://x.org"}
    entry = paper_to_entry(paper, "llmsec-2026-00001", "arxiv", MAPPINGS)
    assert entry["categories"] == ["jailbreaking"]
    assert entry["framework_mappings"] == {"mitre_atlas": ["AML.T0054"], "owasp_llm_top10": ["LLM01"]}
