"""Tests for scripts/fetch_crossref.py."""

from fetch_crossref import clean_text


def test_clean_text_strips_jats_tags():
    assert clean_text("<jats:p>Prompt   injection</jats:p>") == "Prompt injection"


def test_clean_text_handles_double_encoded_markup():
    assert clean_text("&lt;b&gt;Inovasi&lt;/b&gt; Fisika") == "Inovasi Fisika"
