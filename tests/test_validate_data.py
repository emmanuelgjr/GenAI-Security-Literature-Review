"""Tests for scripts/validate_data.py."""

import json
from pathlib import Path

from validate_data import (
    check_category_refs,
    check_duplicate_resources,
    check_framework_refs,
    check_unique_ids,
    check_urls,
    main,
    schema_errors,
)

ROOT = Path(__file__).resolve().parent.parent
TAXONOMY = {"domains": [{"id": "d", "label": "D", "categories": [
    {"id": "prompt-injection", "label": "PI", "framework_mappings": {"owasp_llm_top10": ["LLM01"]}},
]}]}
FRAMEWORKS = {"frameworks": [{"id": "owasp_llm_top10", "entries": [{"id": "LLM01"}]}]}


def entry(**overrides):
    base = {
        "id": "llmsec-2026-00001", "type": "paper", "title": "T", "authors": ["A"], "year": 2026,
        "url": "https://arxiv.org/abs/2609.00001", "categories": ["prompt-injection"],
        "added_date": "2026-09-14", "reviewed": False,
    }
    return {**base, **overrides}


def test_repository_data_is_valid():
    assert main() == 0


def test_schema_errors_enforce_date_format():
    schema = json.loads((ROOT / "schemas" / "literature-entry.schema.json").read_text(encoding="utf-8"))
    assert schema_errors({"entries": [entry()]}, schema) == []
    errors = schema_errors({"entries": [entry(added_date="14/09/2026")]}, schema)
    assert any("added_date" in e for e in errors)


def test_check_unique_ids():
    assert check_unique_ids({"entries": [entry(), entry()]}) == ["  Duplicate ID: llmsec-2026-00001"]


def test_check_duplicate_resources_by_arxiv_id_and_case_insensitive_doi():
    literature = {"entries": [
        entry(id="llmsec-2026-00001", external_ids={"arxiv_id": "2609.00001"}, doi="10.1/ABC"),
        entry(id="llmsec-2026-00002", external_ids={"arxiv_id": "2609.00001"}),
        entry(id="llmsec-2026-00003", external_ids={"doi": "10.1/abc"}),
    ]}
    errors = check_duplicate_resources(literature)
    assert "  DOI 10.1/abc appears in llmsec-2026-00001, llmsec-2026-00003" in errors
    assert "  arXiv 2609.00001 appears in llmsec-2026-00001, llmsec-2026-00002" in errors


def test_check_duplicate_resources_ignores_doi_repeated_within_one_entry():
    literature = {"entries": [entry(doi="10.1/a", external_ids={"doi": "10.1/a"})]}
    assert check_duplicate_resources(literature) == []


def test_check_urls_rejects_relative_and_non_http_links():
    literature = {"entries": [
        entry(id="a", url="arxiv.org/abs/1"),
        entry(id="b", url="javascript:alert(1)"),
        entry(id="c", pdf_url="https://arxiv.org/pdf/1"),
    ]}
    errors = check_urls(literature)
    assert len(errors) == 2
    assert all(e.startswith(("  a:", "  b:")) for e in errors)


def test_check_category_refs():
    errors = check_category_refs({"entries": [entry(categories=["nope"])]}, TAXONOMY)
    assert errors == ["  llmsec-2026-00001: unknown category 'nope'"]


def test_check_framework_refs_covers_entries_and_taxonomy():
    literature = {"entries": [
        entry(framework_mappings={"owasp_llm_top10": ["LLM01", "LLM99"], "made_up": ["X"]}),
    ]}
    taxonomy = {"domains": [{"id": "d", "label": "D", "categories": [
        {"id": "c", "label": "C", "framework_mappings": {"owasp_llm_top10": ["LLM42"]}},
    ]}]}
    errors = check_framework_refs(literature, taxonomy, FRAMEWORKS)
    assert "  llmsec-2026-00001: unknown owasp_llm_top10 entry 'LLM99'" in errors
    assert "  llmsec-2026-00001: unknown framework 'made_up'" in errors
    assert "  taxonomy:c: unknown owasp_llm_top10 entry 'LLM42'" in errors
    assert len(errors) == 3
