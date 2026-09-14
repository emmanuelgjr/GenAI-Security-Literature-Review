"""Tests for scripts/fetch_common.py."""

import json

import pytest
import requests

import fetch_common
from fetch_common import exit_code, get_with_retry, load_source, report, retry_delay


class FakeResponse:
    def __init__(self, status, headers=None):
        self.status_code = status
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)


def scripted_get(monkeypatch, outcomes):
    """Make requests.get return/raise each outcome in turn; returns the call log."""
    calls = []

    def fake_get(url, **kwargs):
        calls.append(kwargs)
        outcome = outcomes[len(calls) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(fetch_common.requests, "get", fake_get)
    return calls


def test_get_with_retry_recovers_from_rate_limit_and_timeout(monkeypatch):
    calls = scripted_get(monkeypatch, [FakeResponse(429), requests.Timeout("slow"), FakeResponse(200)])
    waits = []
    response = get_with_retry("https://example.org", attempts=4, sleep=waits.append)
    assert response.status_code == 200
    assert len(calls) == 3
    assert len(waits) == 2


def test_get_with_retry_gives_up_after_attempts(monkeypatch):
    scripted_get(monkeypatch, [FakeResponse(503)] * 3)
    with pytest.raises(requests.HTTPError):
        get_with_retry("https://example.org", attempts=3, sleep=lambda _: None)


def test_get_with_retry_does_not_retry_client_errors(monkeypatch):
    calls = scripted_get(monkeypatch, [FakeResponse(400), FakeResponse(200)])
    with pytest.raises(requests.HTTPError):
        get_with_retry("https://example.org", sleep=lambda _: None)
    assert len(calls) == 1


def test_get_with_retry_sends_user_agent_and_extra_headers(monkeypatch):
    calls = scripted_get(monkeypatch, [FakeResponse(200)])
    get_with_retry("https://example.org", headers={"x-api-key": "k"})
    assert calls[0]["headers"]["x-api-key"] == "k"
    assert "LLMSecLitReview" in calls[0]["headers"]["User-Agent"]


def test_retry_delay_honours_retry_after_with_cap():
    assert retry_delay(FakeResponse(429, {"Retry-After": "7"}), 0, 10) == 7
    assert retry_delay(FakeResponse(429, {"Retry-After": "9999"}), 0, 10) == fetch_common.MAX_RETRY_WAIT


def test_retry_delay_backs_off_exponentially():
    assert 40 <= retry_delay(None, 2, 10) < 41


def test_exit_code_only_fails_when_nothing_was_fetched():
    assert exit_code([], ["boom"]) == 1
    assert exit_code([{"title": "x"}], ["partial"]) == 0
    assert exit_code([], []) == 0


def test_every_configured_source_is_loadable():
    for source_id in ("arxiv", "semantic-scholar", "crossref"):
        config = load_source(source_id)
        assert config["query_terms"]
        assert config["max_results"] > 0
        assert config["lookback_days"] > 0


def write_sources(tmp_path, sources):
    path = tmp_path / "sources.json"
    path.write_text(json.dumps({"sources": sources}))
    return path


def test_report_flags_failed_missing_and_disabled_sources(tmp_path):
    sources_file = write_sources(tmp_path, [
        {"id": "a", "name": "A", "enabled": True, "candidates_file": "a.json"},
        {"id": "b", "name": "B", "enabled": True, "candidates_file": "b.json"},
        {"id": "c", "name": "C", "enabled": True, "candidates_file": "c.json"},
        {"id": "d", "name": "D", "enabled": False, "candidates_file": "d.json"},
    ])
    (tmp_path / "a.json").write_text(json.dumps({"papers": [{}, {}], "errors": []}))
    (tmp_path / "b.json").write_text(json.dumps({"papers": [], "errors": ["HTTP 429"]}))
    table, any_ok = report(tmp_path, sources_file)
    assert "| A | 2 | :white_check_mark: ok |" in table
    assert "| B | 0 | :x: failed: HTTP 429 |" in table
    assert "| C | 0 | :x: no output" in table
    assert "| D | - | disabled |" in table
    assert any_ok


def test_report_fails_when_no_source_delivers(tmp_path):
    sources_file = write_sources(tmp_path, [
        {"id": "a", "name": "A", "enabled": True, "candidates_file": "a.json"},
    ])
    (tmp_path / "a.json").write_text(json.dumps({"papers": [], "errors": ["HTTP 429"]}))
    _, any_ok = report(tmp_path, sources_file)
    assert not any_ok
