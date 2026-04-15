# Contributing to GenAI Security Literature Review

Thank you for helping build the most comprehensive open resource for GenAI and LLM security research.

## How to Contribute

### Adding a Resource (Easiest)

1. Open a [new issue](../../issues/new?template=add-resource.md) using the "Add Resource" template
2. Fill in the required fields (title, URL, type, categories)
3. A maintainer will review and add it to the database

### Direct Contribution via Pull Request

1. Fork this repository
2. Add your entry to `data/literature.json` following the schema in `schemas/literature-entry.schema.json`
3. Run validation: `python scripts/validate_data.py`
4. Submit a PR using the pull request template

### Entry Format

Each entry in `data/literature.json` requires at minimum:

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Format: `llmsec-YYYY-NNNNN` |
| `type` | Yes | One of: paper, book, report, tool, standard, talk, blog, dataset |
| `title` | Yes | Full title |
| `authors` | Yes | Array of author names |
| `year` | Yes | Publication year |
| `url` | Yes | Link to the resource |
| `categories` | Yes | Array of category IDs from `data/taxonomy.json` |
| `reviewed` | Yes | Set to `false` for new submissions |

See `schemas/literature-entry.schema.json` for the complete schema with all optional fields.

### Category IDs

Browse `data/taxonomy.json` for valid category IDs. If you think a new category is needed, mention it in your PR description.

## Guidelines

- One entry per resource (don't combine multiple papers into one entry)
- Use the canonical URL (prefer DOI links, then publisher, then arXiv)
- Write concise abstracts (2-3 sentences) if the original is very long
- Tag framework mappings (OWASP, NIST, MITRE) when applicable
- Check for duplicates before submitting

## Development

### Prerequisites

- Python 3.9+ (for automation scripts)
- Node.js 18+ (for the webapp)

### Local Setup

```bash
# Validate data
pip install -r scripts/requirements.txt
python scripts/validate_data.py

# Run webapp locally
cd webapp
npm install
npm run dev
```

## Code of Conduct

Be respectful, constructive, and inclusive. We follow the [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).
