# Security Policy

## Scope

This repository contains a static literature review database and webapp. It does **not** process user authentication, store credentials, or handle sensitive data at runtime. The primary security considerations are:

- **Data integrity** of the literature database (`data/literature.json`)
- **Supply chain security** of npm and Python dependencies
- **GitHub Actions workflow security** (automated paper fetching, deployment)
- **Static site security** (the deployed GitHub Pages webapp)

## Supported Versions

| Component | Version | Supported |
|-----------|---------|-----------|
| Webapp (Astro) | latest on `main` | Yes |
| Data schema | v1.0 | Yes |
| Python scripts | latest on `main` | Yes |

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly:

1. **Do NOT open a public GitHub issue** for security vulnerabilities
2. **Email**: Send details to [emmanuelgjr@gmail.com](mailto:emmanuelgjr@gmail.com)
3. **Include**: Description of the vulnerability, steps to reproduce, and potential impact
4. **Response time**: You can expect an initial response within 72 hours

## Security Measures

- **Automated dependency updates** via Dependabot (npm, pip, GitHub Actions)
- **CodeQL analysis** on every push and pull request
- **JSON Schema validation** on all data changes via CI
- **Human review required** for all automated paper additions (PRs, not direct commits)
- **No secrets or API keys** stored in the repository

## Dependencies

This project uses:
- **Astro** (static site generator) -- no server-side execution in production
- **Preact** (lightweight UI) -- client-side only, no data submission
- **Python** (automation scripts) -- runs only in GitHub Actions, not user-facing
- **Fuse.js** (client-side search) -- no external API calls

The webapp is deployed as static HTML/CSS/JS to GitHub Pages with no server-side processing.
