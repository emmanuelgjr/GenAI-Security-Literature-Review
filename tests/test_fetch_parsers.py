"""Tests for the response parsers in scripts/fetch_*.py."""

import pytest

from fetch_arxiv import build_query, parse_feed
from fetch_crossref import clean_text
from fetch_crossref import parse_items as parse_crossref
from fetch_semantic_scholar import parse_items as parse_s2

ARXIV_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2609.01234v2</id>
    <published>2026-09-10T17:00:00Z</published>
    <title>Prompt Injection
      Against Web Agents</title>
    <summary>  We study   indirect prompt injection. </summary>
    <author><name>A. Author</name></author>
    <author><name>B. Author</name></author>
    <link title="pdf" href="https://arxiv.org/pdf/2609.01234v2"/>
    <arxiv:doi>10.1000/xyz</arxiv:doi>
    <category term="cs.CR"/>
  </entry>
</feed>"""

ARXIV_ERROR = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry><id>http://arxiv.org/api/errors#incorrect_id</id><summary>bad query</summary></entry>
</feed>"""

ENTITY_PAYLOAD = b"""<?xml version="1.0"?>
<!DOCTYPE feed [<!ENTITY a "aaaa">]>
<feed xmlns="http://www.w3.org/2005/Atom">&a;</feed>"""


def test_parse_feed_extracts_normalised_fields():
    [paper] = parse_feed(ARXIV_FEED)
    assert paper["title"] == "Prompt Injection Against Web Agents"
    assert paper["abstract"] == "We study indirect prompt injection."
    assert paper["arxiv_id"] == "2609.01234"
    assert paper["url"] == "https://arxiv.org/abs/2609.01234"
    assert (paper["year"], paper["month"], paper["published"]) == (2026, 9, "2026-09-10")
    assert paper["authors"] == ["A. Author", "B. Author"]
    assert paper["doi"] == "10.1000/xyz"
    assert paper["arxiv_categories"] == ["cs.CR"]


def test_parse_feed_raises_on_api_error_entry():
    with pytest.raises(ValueError, match="bad query"):
        parse_feed(ARXIV_ERROR)


def test_parse_feed_refuses_entity_declarations():
    with pytest.raises(Exception):
        parse_feed(ENTITY_PAYLOAD)


def test_build_query_ors_parenthesised_terms():
    assert build_query(["a AND b", "c"]) == "(a AND b) OR (c)"


def test_parse_s2_maps_external_ids_and_skips_untitled():
    papers = parse_s2([
        {
            "paperId": "p1", "title": "Jailbreaking LLMs", "authors": [{"name": "X"}, {}],
            "year": 2026, "publicationDate": "2026-08-15",
            "externalIds": {"DOI": "10.1/a", "ArXiv": "2608.1"},
            "abstract": None, "url": "https://s2/p1", "venue": "ICLR",
        },
        {"paperId": "p2", "title": None},
    ])
    assert len(papers) == 1
    paper = papers[0]
    assert (paper["doi"], paper["arxiv_id"], paper["semantic_scholar_id"]) == ("10.1/a", "2608.1", "p1")
    assert paper["month"] == 8
    assert paper["authors"] == ["X"]
    assert paper["abstract"] == ""


def test_parse_crossref_cleans_markup_and_reads_venue():
    [paper] = parse_crossref([{
        "DOI": "10.2/b",
        "title": ["&lt;i&gt;RAG&lt;/i&gt; Poisoning"],
        "author": [{"given": "Ada", "family": "L"}, {"family": ""}],
        "published-online": {"date-parts": [[2026, 5]]},
        "abstract": "<jats:p>Abstract</jats:p>",
        "container-title": ["Journal of AI Security"],
    }])
    assert paper["title"] == "RAG Poisoning"
    assert paper["authors"] == ["Ada L"]
    assert (paper["year"], paper["month"]) == (2026, 5)
    assert paper["url"] == "https://doi.org/10.2/b"
    assert paper["venue"] == "Journal of AI Security"
    assert paper["abstract"] == "Abstract"


def test_clean_text_strips_jats_tags():
    assert clean_text("<jats:p>Prompt   injection</jats:p>") == "Prompt injection"


def test_clean_text_handles_double_encoded_markup():
    assert clean_text("&lt;b&gt;Inovasi&lt;/b&gt; Fisika") == "Inovasi Fisika"
