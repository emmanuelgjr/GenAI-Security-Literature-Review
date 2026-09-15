"""Tests for scripts/check_links.py and scripts/verify_entries.py (no network)."""

import pytest

import verify_entries
from check_links import Result, classify, link_targets, report as link_report
from verify_entries import arxiv_id_of, author_overlap, doi_of, verify


# --- check_links ---

def test_link_targets_skips_arxiv_and_missing_fields():
    literature = {"entries": [
        {"id": "a", "url": "https://arxiv.org/abs/2401.00001", "pdf_url": "https://arxiv.org/pdf/2401.00001"},
        {"id": "b", "url": "https://owasp.org/x", "pdf_url": None},
        {"id": "c", "url": "https://doi.org/10.1/x", "pdf_url": "https://example.org/c.pdf"},
    ]}
    assert [(e["id"], field) for e, field, _ in link_targets(literature)] == [
        ("b", "url"), ("c", "url"), ("c", "pdf_url"),
    ]


@pytest.mark.parametrize("status, is_doi, expected", [
    (200, False, "ok"),
    (301, False, "ok"),
    (404, False, "broken"),
    (410, False, "broken"),
    (403, False, "unverifiable"),
    (429, False, "unverifiable"),
    (302, True, "ok"),      # doi.org redirects registered DOIs
    (404, True, "broken"),  # and 404s unknown ones
])
def test_classify(status, is_doi, expected):
    assert classify(status, is_doi) == expected


def test_link_report_separates_broken_from_unverifiable_and_escapes_pipes():
    text = link_report([
        Result("e1", "A | B", "url", "https://x.org", "broken", "HTTP 404"),
        Result("e2", "C", "url", "https://y.org", "unverifiable", "HTTP 403"),
        Result("e3", "D", "url", "https://z.org", "ok", "HTTP 200"),
    ])
    assert "**1 broken**, 1 could not be verified" in text
    assert "A \\| B" in text
    assert text.index("### Broken") < text.index("### Could not verify")
    assert "z.org" not in text


# --- verify_entries ---

def test_arxiv_id_of_prefers_external_ids_then_url():
    assert arxiv_id_of({"external_ids": {"arxiv_id": "2402.11082"}, "url": "https://x.org"}) == "2402.11082"
    assert arxiv_id_of({"url": "https://arxiv.org/pdf/2310.08419"}) == "2310.08419"
    assert arxiv_id_of({"url": "https://arxiv.org/abs/cs/0701001"}) == "cs/0701001"
    assert arxiv_id_of({"url": "https://example.org"}) == ""


def test_doi_of_reads_either_field():
    assert doi_of({"doi": "10.1/a"}) == "10.1/a"
    assert doi_of({"external_ids": {"doi": "10.1/b"}}) == "10.1/b"


def fake_sources(monkeypatch, arxiv=None, crossref=None):
    monkeypatch.setattr(verify_entries, "arxiv_record", lambda _id: arxiv)
    monkeypatch.setattr(verify_entries, "crossref_record", lambda _doi: crossref)


def test_verify_accepts_matching_titles_despite_case_and_punctuation(monkeypatch):
    fake_sources(monkeypatch, arxiv=("The AI security pyramid of pain", ["Chris M. Ward"]))
    entry = {"id": "e", "title": "The AI Security Pyramid of Pain", "external_ids": {"arxiv_id": "2402.11082"}}
    assert verify(entry, sleep=lambda _: None) == []


def test_verify_flags_identifier_pointing_at_another_paper(monkeypatch):
    fake_sources(monkeypatch, arxiv=("Wing Optimisation for a tractor propeller driven Micro Aerial Vehicle", []))
    entry = {"id": "e", "title": "ConfusedPilot: Confused Deputy Attacks Against RAG-based Code Assistants",
             "url": "https://arxiv.org/abs/2409.12345"}
    [finding] = verify(entry, sleep=lambda _: None)
    assert finding.problem == "title mismatch"
    assert finding.identifier == "arXiv:2409.12345"


def test_verify_flags_unknown_identifier(monkeypatch):
    fake_sources(monkeypatch, crossref=None)
    entry = {"id": "e", "title": "T", "url": "https://example.org", "doi": "10.5555/3489212.3489351"}
    [finding] = verify(entry, sleep=lambda _: None)
    assert finding.problem == "identifier not found"


def test_verify_flags_right_title_with_wrong_authors(monkeypatch):
    fake_sources(monkeypatch, arxiv=(
        "Jailbreaking Leading Safety-Aligned LLMs with Simple Adaptive Attacks",
        ["Maksym Andriushchenko", "Francesco Croce", "Nicolas Flammarion"],
    ))
    entry = {"id": "e", "title": "Jailbreaking Leading Safety-Aligned LLMs with Simple Adaptive Attacks",
             "authors": ["Jingwei Yi", "Yueqi Xie", "Bin Zhu"], "external_ids": {"arxiv_id": "2404.02151"}}
    [finding] = verify(entry, sleep=lambda _: None)
    assert finding.problem == "author mismatch"
    assert "Andriushchenko" in finding.found_title


def test_author_overlap_folds_accents_and_ignores_organisations():
    assert author_overlap(["Florian Tramer"], ["Florian Tramèr"]) == 1.0
    assert author_overlap(["Microsoft AI Red Team"], ["Someone Else"]) is None
    assert author_overlap(["Ada Lovelace", "Alan Turing"], ["A. Lovelace", "C. Babbage"]) == 0.5
    assert author_overlap(["Ada Lovelace"], []) is None
