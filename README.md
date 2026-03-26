# Medienrechtspraxis

Open-access, AI-generated, daily-updated legal commentary on Swiss media law and personality rights.

## Architecture

- **`content/`** — Generated legal content, organized by topic (3 layers: summary, doctrine, caselaw)
- **`agents/`** — Python pipeline for content generation, evaluation, and translation
- **`guidelines/`** — Quality standards and topic-specific generation context
- **`site/`** — Astro 4.x static site
- **`mcp-server/`** — MCP server exposing content to LLMs
- **`scripts/`** — Utility scripts for data fetching and bootstrapping
- **`.github/workflows/`** — CI/CD: daily update, site build, MCP deploy

## Quick Start

### Prerequisites

- Python 3.12+ with [uv](https://docs.astral.sh/uv/)
- Node.js 20+
- Anthropic API key (`ANTHROPIC_API_KEY`)

### Install

```bash
# Python pipeline
uv sync

# Astro site
cd site && npm install

# MCP server
cd mcp-server && npm install
```

### Bootstrap Content

```bash
# Single topic
uv run python -m agents.pipeline bootstrap --topic persoenlichkeitsschutz

# All topics (with budget cap in USD)
uv run python -m agents.pipeline bootstrap --all --max-budget 100

# Resume interrupted bootstrap
uv run python -m agents.pipeline bootstrap --state-file state.json
```

### Run Site Locally

```bash
cd site
npm run dev
```

### Run MCP Server Locally

```bash
cd mcp-server
npm run dev
```

## Content Model

Each topic has three layers:

| Layer | Audience | Style |
|-------|----------|-------|
| **Summary** (Praxis) | Journalists, editors | Plain language, checklists, 300–500 words |
| **Doctrine** (Doktrin) | Lawyers | Academic with Randziffern, DACH comparison, 1500–3000 words |
| **Caselaw** (Rechtsprechung) | Both | Case digests, chronological, significance-rated |

## Daily Update Pipeline

Runs nightly via GitHub Actions:

1. Query opencaselaw MCP for new decisions
2. Filter for media-law relevance
3. Regenerate affected topic layers
4. Evaluate quality (5 non-negotiables + 5 scored dimensions)
5. Translate passing content DE → EN
6. Auto-commit and deploy

## License

Content: CC-BY-SA 4.0  
Code: MIT
