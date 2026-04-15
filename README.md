# GenAI Security Literature Review

[![Validate Data](https://github.com/emmanuelgjr/GenAI-Security-Literature-Review/actions/workflows/validate-data.yml/badge.svg)](https://github.com/emmanuelgjr/GenAI-Security-Literature-Review/actions/workflows/validate-data.yml)
[![Deploy Webapp](https://github.com/emmanuelgjr/GenAI-Security-Literature-Review/actions/workflows/deploy-webapp.yml/badge.svg)](https://github.com/emmanuelgjr/GenAI-Security-Literature-Review/actions/workflows/deploy-webapp.yml)
[![Fetch Papers](https://github.com/emmanuelgjr/GenAI-Security-Literature-Review/actions/workflows/fetch-papers.yml/badge.svg)](https://github.com/emmanuelgjr/GenAI-Security-Literature-Review/actions/workflows/fetch-papers.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive, community-driven, auto-updating literature review of **GenAI and LLM security** research, standards, tools, and resources. Currently tracking **100 resources** across **42 categories** with weekly automated updates from academic APIs.

**[Browse the Interactive Webapp](https://emmanuelgjr.github.io/GenAI-Security-Literature-Review/)**

## What's Inside

This repository maintains a curated and continuously growing database of GenAI/LLM security resources spanning:

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

A weekly GitHub Action queries academic APIs (arXiv, Semantic Scholar, CrossRef) for new GenAI security publications. New entries are submitted as pull requests for human review before merging.

### Community Contributions

Anyone can submit resources via [GitHub Issues](https://github.com/emmanuelgjr/GenAI-Security-Literature-Review/issues/new?template=add-resource.md) or pull requests. See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### Interactive Webapp

The static webapp (deployed to GitHub Pages) provides:
- Full-text fuzzy search across all entries
- Color-coded category browsing by domain
- Filter by type, year, framework mapping, and review status
- Framework mapping explorer (OWASP, NIST, MITRE, ISO)
- Individual entry detail pages with BibTeX citation export

## Repository Structure

```
data/
  literature.json      # Core database (100 curated entries)
  taxonomy.json        # 8 domains, 42 category definitions
  frameworks.json      # OWASP/NIST/MITRE/ISO framework definitions
  sources.json         # Automation source configuration
schemas/               # JSON Schema for data validation
scripts/               # Python automation (fetch, dedup, validate)
webapp/                # Astro static site (Preact + Tailwind)
.github/workflows/     # CI/CD (validation, weekly fetch, deploy)
```

## Quick Start

### Browse Online

Visit the **[Interactive Webapp](https://emmanuelgjr.github.io/GenAI-Security-Literature-Review/)** -- no installation needed.

### Run Locally

```bash
git clone https://github.com/emmanuelgjr/GenAI-Security-Literature-Review.git
cd GenAI-Security-Literature-Review

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

**Emmanuel Guilherme** ([@emmanuelgjr](https://github.com/emmanuelgjr)) -- OWASP contributor, GenAI data security researcher.
