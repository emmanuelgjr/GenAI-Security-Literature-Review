# GenAI Security Literature Review

[![Validate Data](../../actions/workflows/validate-data.yml/badge.svg)](../../actions/workflows/validate-data.yml)
[![Deploy Webapp](../../actions/workflows/deploy-webapp.yml/badge.svg)](../../actions/workflows/deploy-webapp.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive, community-driven, auto-updating literature review of **GenAI and LLM security** research, standards, tools, and resources.

**[Browse the Interactive Webapp](https://emmanuelgjr.github.io/LLM-Security-Literature-Review/)**

## What's Inside

This repository maintains a curated and continuously growing database of LLM/AI security resources spanning:

### Categories

| Domain | Topics |
|--------|--------|
| **Attacks & Threats** | Prompt injection, jailbreaking, data poisoning, model extraction, membership inference, adversarial examples, supply chain, social engineering, agentic threats |
| **Defenses & Mitigations** | Input filtering, output moderation, guardrails, access control, monitoring, sandboxing, cryptographic controls, watermarking |
| **Privacy** | Differential privacy, federated learning, data anonymization, machine unlearning, confidential computing |
| **Governance & Compliance** | Risk frameworks (NIST, ISO, EU AI Act), model governance, audit & assurance, responsible AI, incident response |
| **Red Teaming & Evaluation** | Red teaming methodology, safety benchmarks, LLM fuzzing, vulnerability disclosure |
| **Infrastructure & Deployment** | Model serving security, RAG security, fine-tuning security, MLOps, cloud AI security |
| **Agentic AI Security** | Agent architecture, tool-use security, memory security, human-in-the-loop, autonomous operations |
| **Surveys & Meta** | Literature surveys, threat modeling, industry reports, books, conference proceedings |

### Framework Mappings

Every entry is mapped (where applicable) to:
- **OWASP Top 10 for LLM Applications**
- **OWASP Top 10 for Agentic AI**
- **MITRE ATLAS** (Adversarial Threat Landscape for AI Systems)
- **NIST AI Risk Management Framework**
- **ISO/IEC 42001** (AI Management System)

## How It Works

### Auto-Discovery

A weekly GitHub Action queries academic APIs (arXiv, Semantic Scholar, CrossRef) for new LLM security publications. New entries are submitted as pull requests for human review before merging.

### Community Contributions

Anyone can submit resources via [GitHub Issues](../../issues/new?template=add-resource.md) or pull requests. See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### Interactive Webapp

The static webapp (deployed to GitHub Pages) provides:
- Full-text search across all entries
- Browse by category taxonomy
- Filter by type, year, framework mapping, and review status
- Individual entry detail pages with citation export

## Repository Structure

```
data/
  literature.json      # Core database of all entries
  taxonomy.json        # Category definitions
  frameworks.json      # Security framework definitions
  sources.json         # Automation source configuration
schemas/               # JSON Schema for data validation
scripts/               # Python automation (fetch, dedup, validate)
webapp/                # Astro static site
.github/workflows/     # CI/CD (validation, fetch, deploy)
```

## Quick Start

### Browse Online

Visit the **[Interactive Webapp](https://emmanuelgjr.github.io/LLM-Security-Literature-Review/)** -- no installation needed.

### Run Locally

```bash
# Clone
git clone https://github.com/emmanuelgjr/LLM-Security-Literature-Review.git
cd LLM-Security-Literature-Review

# Run the webapp
cd webapp
npm install
npm run dev
```

### Validate Data

```bash
pip install -r scripts/requirements.txt
python scripts/validate_data.py
```

## Contributing

We welcome contributions of all kinds -- new papers, tools, corrections, framework mappings, and webapp improvements. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

This work is licensed under the [MIT License](LICENSE).

## Maintainer

**Emmanuel Gonzalez** ([@emmanuelgjr](https://github.com/emmanuelgjr)) -- OWASP contributor, GenAI data security researcher.
