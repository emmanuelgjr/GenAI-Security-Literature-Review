"""Tests for scripts/deduplicate.py."""

import pytest

from deduplicate import (
    auto_categorize,
    build_existing_index,
    get_next_id,
    is_duplicate,
    is_on_topic,
    is_valid_candidate,
    normalize_title,
    title_similarity,
)


# --- normalize_title ---

def test_normalize_title_lowercases_and_strips_punctuation():
    assert normalize_title("Hello, World!") == "hello world"


def test_normalize_title_collapses_whitespace():
    assert normalize_title("  multiple   spaces\there  ") == "multiple spaces here"


# --- title_similarity ---

def test_title_similarity_identical_titles():
    assert title_similarity("Prompt Injection Attacks", "Prompt Injection Attacks") == 1.0


def test_title_similarity_disjoint_titles():
    assert title_similarity("Prompt Injection", "Federated Learning") == 0.0


def test_title_similarity_empty_returns_zero():
    assert title_similarity("", "anything") == 0.0


def test_title_similarity_is_word_order_invariant():
    # Jaccard on word sets ignores word order
    assert title_similarity("Jailbreaking LLMs", "LLMs Jailbreaking") == 1.0


# --- is_valid_candidate ---

def test_valid_candidate_accepts_well_formed():
    ok, _ = is_valid_candidate({
        "title": "A Paper",
        "authors": ["X. Author"],
        "year": 2024,
        "url": "https://example.org/p",
    })
    assert ok


def test_valid_candidate_rejects_missing_year():
    ok, reason = is_valid_candidate({
        "title": "A Paper",
        "authors": ["X"],
        "year": None,
        "url": "https://example.org/p",
    })
    assert not ok
    assert "year" in reason


def test_valid_candidate_rejects_year_too_old():
    ok, _ = is_valid_candidate({
        "title": "Old", "authors": ["X"], "year": 1999, "url": "https://example.org",
    })
    assert not ok


def test_valid_candidate_rejects_empty_authors():
    ok, reason = is_valid_candidate({
        "title": "T", "authors": [], "year": 2024, "url": "https://example.org",
    })
    assert not ok
    assert "authors" in reason


def test_valid_candidate_rejects_blank_title():
    ok, reason = is_valid_candidate({
        "title": "  ", "authors": ["X"], "year": 2024, "url": "https://example.org",
    })
    assert not ok
    assert "title" in reason


def test_valid_candidate_rejects_blank_url():
    ok, reason = is_valid_candidate({
        "title": "T", "authors": ["X"], "year": 2024, "url": "",
    })
    assert not ok
    assert "url" in reason


# --- auto_categorize ---

def test_auto_categorize_prompt_injection():
    assert "prompt-injection" in auto_categorize("a paper about prompt injection")


def test_auto_categorize_returns_empty_for_off_topic():
    assert auto_categorize("paper about sustainable agriculture yields") == []


def test_auto_categorize_finds_multiple_categories():
    cats = auto_categorize("jailbreak via adversarial perturbation")
    assert "jailbreaking" in cats
    assert "adversarial-examples" in cats


def test_auto_categorize_dedupes_when_multiple_keywords_hit_same_category():
    # Both "jailbreak" and "jailbreaking" map to the same category
    cats = auto_categorize("jailbreak and jailbreaking on llms")
    assert cats.count("jailbreaking") == 1


# --- is_on_topic ---

def test_is_on_topic_true_for_security_paper():
    paper = {"title": "Prompt Injection on LLMs", "abstract": ""}
    assert is_on_topic(paper)


def test_is_on_topic_false_for_unrelated_paper():
    paper = {
        "title": "Sustainable agriculture techniques",
        "abstract": "Optimizing crop yield via rotation",
    }
    assert not is_on_topic(paper)


# --- build_existing_index + is_duplicate ---

@pytest.fixture
def small_library():
    literature = {"entries": [
        {
            "id": "llmsec-2024-00001",
            "title": "Prompt Injection Attacks on LLMs",
            "external_ids": {"arxiv_id": "2401.12345", "doi": "10.1234/abcd"},
        },
        {
            "id": "llmsec-2024-00002",
            "title": "Adversarial Examples in Vision Models",
            "external_ids": {"semantic_scholar_id": "s2-xyz"},
        },
    ]}
    return literature, build_existing_index(literature)


def test_is_duplicate_by_arxiv_id(small_library):
    _, index = small_library
    assert is_duplicate({"arxiv_id": "2401.12345", "title": "Different title here"}, index)


def test_is_duplicate_by_doi_case_insensitive(small_library):
    _, index = small_library
    assert is_duplicate({"doi": "10.1234/ABCD", "title": "Different title here"}, index)


def test_is_duplicate_by_semantic_scholar_id(small_library):
    _, index = small_library
    assert is_duplicate({"semantic_scholar_id": "s2-xyz", "title": "Different"}, index)


def test_is_duplicate_by_title_similarity(small_library):
    _, index = small_library
    # Same word set as the indexed title, just reordered with punctuation
    assert is_duplicate({"title": "Attacks on LLMs: Prompt Injection!"}, index)


def test_is_not_duplicate_when_distinct(small_library):
    _, index = small_library
    assert not is_duplicate({"title": "Differential Privacy in Federated Learning"}, index)


# --- get_next_id ---

def test_get_next_id_increments_max():
    literature = {"entries": [
        {"id": "llmsec-2024-00007"},
        {"id": "llmsec-2024-00003"},
        {"id": "llmsec-2024-00099"},
    ]}
    assert get_next_id(literature) == 100


def test_get_next_id_returns_one_for_empty_library():
    assert get_next_id({"entries": []}) == 1
