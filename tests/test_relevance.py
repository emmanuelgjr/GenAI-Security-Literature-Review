"""Tests for the review hints in scripts/relevance.py and the PR summary in deduplicate.py."""

import pytest

from deduplicate import review_summary
from relevance import confidence, scope_note


@pytest.mark.parametrize("title, expected", [
    ("Jailbreaking Large Language Models via Persona Prompts", "high"),
    ("Backdoor Attacks on Decentralised Post-Training", "medium"),        # security term only
    ("SKILL.state: Scalable Long-Horizon Agent Skills for LLMs", "medium"),  # GenAI term only
    ("Automated alignment is harder than you think", "low"),
])
def test_confidence_reads_the_title(title, expected):
    # The abstract is ignored: every accepted paper already matched somewhere
    assert confidence({"title": title, "abstract": "prompt injection against LLMs"}) == expected


def test_scope_note_flags_ai_for_security_papers():
    paper = {"title": "Agentic AI for Autonomous Threat Hunting and Intrusion Detection", "abstract": ""}
    assert scope_note(paper) == "possibly AI-for-security (check scope)"


def test_scope_note_ignores_attacks_on_ai_security_tools():
    paper = {
        "title": "Defending Retrieval-Augmented Intrusion Detection Against Knowledge Poisoning",
        "abstract": "",
    }
    assert scope_note(paper) is None


def test_scope_note_is_none_for_core_papers():
    assert scope_note({"title": "Indirect Prompt Injection in Web Agents", "abstract": ""}) is None


def test_review_summary_lists_weakest_matches_first_with_counts():
    entries = [
        {"id": "h", "title": "Prompt Injection Attacks on LLM Agents", "url": "u1", "categories": ["prompt-injection"]},
        {"id": "l", "title": "Automated alignment is harder than you think", "url": "u2", "categories": ["guardrails"]},
        {"id": "s", "title": "LLM agents for malware analysis security", "url": "u3", "categories": ["agentic-threats"]},
    ]
    summary = review_summary(entries)
    assert summary.index("## Low confidence (1)") < summary.index("## High confidence (2)")
    assert "## Medium confidence" not in summary
    assert "Categories: agentic-threats  <- possibly AI-for-security (check scope)" in summary
    assert summary.splitlines()[0] == "## Low confidence (1)"
