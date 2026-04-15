## What does this PR do?

<!-- Brief description of the changes -->

## Checklist

- [ ] Entries follow the schema in `schemas/literature-entry.schema.json`
- [ ] IDs are unique and follow `llmsec-YYYY-NNNNN` format
- [ ] All `categories` values exist in `data/taxonomy.json`
- [ ] Framework mappings use valid IDs from `data/frameworks.json`
- [ ] No duplicate entries (checked by DOI, arXiv ID, or title)
- [ ] URLs are valid and accessible
- [ ] `reviewed` field is set appropriately
- [ ] `python scripts/validate_data.py` passes locally
