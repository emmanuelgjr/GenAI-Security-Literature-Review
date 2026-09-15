#!/usr/bin/env python3
"""Keyword relevance rules for candidate papers: topic gate, categories, review hints.

Used by deduplicate.py to decide what enters the weekly auto-fetch PR and to
order that PR's summary so reviewers see the weakest matches first.
"""

from __future__ import annotations

import re

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


# Security terms that describe *using* AI for security work. A paper matching
# these but none of ATTACK_ON_AI_RE is likely "AI for security" (e.g. LLM-based
# malware detection) rather than security *of* AI, which is this review's scope.
AI_FOR_SECURITY_RE = re.compile(
    r"(?<![a-z0-9])(?:"
    r"malware|intrusion detection|vulnerability detection|penetration testing|pentest\w*"
    r"|threat intelligence|threat hunting|phishing detection|soc analysts?|security operations"
    r"|cyber defen[cs]e|smart contracts?|code vulnerabilit\w*|exploit generation|ctf"
    r")(?![a-z0-9])"
)
ATTACK_ON_AI_RE = re.compile(
    r"(?<![a-z0-9])(?:"
    r"prompt[- ]injection|jailbreak\w*|poison\w*|backdoor\w*|adversarial|guardrails?"
    r"|membership inference|model (?:stealing|extraction)|red[- ]?team\w*|alignment"
    r")(?![a-z0-9])"
)

CONFIDENCE_LEVELS = ("low", "medium", "high")


def confidence(paper: dict) -> str:
    """How strongly the *title* signals GenAI security: "high", "medium" or "low".

    Every accepted paper already matched in title or abstract; papers whose
    title carries neither signal are the ones most often off-topic.
    """
    title = (paper.get("title") or "").lower()
    signals = bool(GENAI_RE.search(title)) + bool(SECURITY_RE.search(title))
    return CONFIDENCE_LEVELS[signals]


def scope_note(paper: dict) -> str | None:
    """A reviewer hint when the paper looks like AI *for* security rather than *of* AI."""
    text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
    if AI_FOR_SECURITY_RE.search(text) and not ATTACK_ON_AI_RE.search(text):
        return "possibly AI-for-security (check scope)"
    return None
