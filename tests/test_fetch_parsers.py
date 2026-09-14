"""Tests for the response parsers in scripts/fetch_*.py."""

import pytest

from fetch_arxiv import harvest_set, parse_records, submission_month
from fetch_crossref import clean_text
from fetch_crossref import parse_items as parse_crossref
from fetch_semantic_scholar import parse_items as parse_s2

OAI_PAGE = b"""<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
  <ListRecords>
    <record>
      <header><identifier>oai:arXiv.org:2609.01234</identifier><datestamp>2026-09-11</datestamp></header>
      <metadata>
        <arXiv xmlns="http://arxiv.org/OAI/arXiv/">
          <id>2609.01234</id>
          <created>2026-09-10</created>
          <authors>
            <author><keyname>Author</keyname><forenames>Ada</forenames></author>
            <author><keyname>Collaboration</keyname></author>
          </authors>
          <title>Prompt Injection
            Against Web Agents</title>
          <categories>cs.CR cs.CL</categories>
          <doi>10.1000/xyz</doi>
          <abstract>  We study   indirect prompt injection. </abstract>
        </arXiv>
      </metadata>
    </record>
    <record>
      <header status="deleted"><identifier>oai:arXiv.org:2609.09999</identifier></header>
    </record>
    <resumptionToken expirationDate="2026-09-15T00:00:00Z">verb%3DListRecords%26skip%3D1</resumptionToken>
  </ListRecords>
</OAI-PMH>"""

OAI_LAST_PAGE = b"""<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"><ListRecords><resumptionToken/></ListRecords></OAI-PMH>"""

OAI_NO_RECORDS = b"""<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"><error code="noRecordsMatch">none</error></OAI-PMH>"""

OAI_BAD_ARGUMENT = b"""<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"><error code="badArgument">bad set</error></OAI-PMH>"""

ENTITY_PAYLOAD = b"""<?xml version="1.0"?>
<!DOCTYPE OAI-PMH [<!ENTITY a "aaaa">]>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">&a;</OAI-PMH>"""


def test_parse_records_extracts_normalised_fields_and_token():
    papers, token = parse_records(OAI_PAGE)
    assert token == "verb%3DListRecords%26skip%3D1"
    [paper] = papers  # the deleted record is skipped
    assert paper["title"] == "Prompt Injection Against Web Agents"
    assert paper["abstract"] == "We study indirect prompt injection."
    assert paper["arxiv_id"] == "2609.01234"
    assert paper["url"] == "https://arxiv.org/abs/2609.01234"
    assert (paper["year"], paper["month"]) == (2026, 9)
    assert paper["authors"] == ["Ada Author", "Collaboration"]
    assert paper["doi"] == "10.1000/xyz"
    assert paper["arxiv_categories"] == ["cs.CR", "cs.CL"]


def test_parse_records_treats_empty_token_and_no_records_as_done():
    assert parse_records(OAI_LAST_PAGE) == ([], None)
    assert parse_records(OAI_NO_RECORDS) == ([], None)


def test_parse_records_raises_on_protocol_error():
    with pytest.raises(ValueError, match="badArgument"):
        parse_records(OAI_BAD_ARGUMENT)


def test_parse_records_refuses_entity_declarations():
    with pytest.raises(Exception):
        parse_records(ENTITY_PAYLOAD)


@pytest.mark.parametrize("arxiv_id, expected", [
    ("2609.01234", (2026, 9)),
    ("2204.07228", (2022, 4)),  # revised in 2026, but first submitted in 2022
    ("0704.0001", (2007, 4)),
    ("cs/9901001", (1999, 1)),
    ("not-an-id", None),
])
def test_submission_month_reads_the_identifier(arxiv_id, expected):
    assert submission_month(arxiv_id) == expected


def test_harvest_set_follows_resumption_tokens(monkeypatch):
    pages = [OAI_PAGE, OAI_LAST_PAGE]
    requests_made = []

    class Response:
        def __init__(self, content):
            self.content = content

    def fake_get(url, *, params, **kwargs):
        requests_made.append(params)
        return Response(pages[len(requests_made) - 1])

    monkeypatch.setattr("fetch_arxiv.get_with_retry", fake_get)
    papers = harvest_set("https://oai", "cs:cs:CR", "2026-09-01", sleep=lambda _: None)
    assert len(papers) == 1
    assert requests_made[0]["set"] == "cs:cs:CR" and requests_made[0]["from"] == "2026-09-01"
    assert requests_made[1] == {"verb": "ListRecords", "resumptionToken": "verb%3DListRecords%26skip%3D1"}


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


def test_parse_crossref_falls_back_to_issued_date():
    [paper] = parse_crossref([{
        "DOI": "10.3/c", "title": ["PIDL: A Prompt Injection Detection Layer"],
        "author": [{"given": "A", "family": "B"}],
        "published-online": {"date-parts": [[None]]},
        "issued": {"date-parts": [[2026, 9, 3]]},
    }])
    assert (paper["year"], paper["month"]) == (2026, 9)


def test_clean_text_strips_jats_tags():
    assert clean_text("<jats:p>Prompt   injection</jats:p>") == "Prompt injection"


def test_clean_text_handles_double_encoded_markup():
    assert clean_text("&lt;b&gt;Inovasi&lt;/b&gt; Fisika") == "Inovasi Fisika"
