# Medienrechtspraxis — Design Specification

## Vision

Open-access, AI-generated, daily-updated legal commentary on Swiss media law and personality rights. Designed for practitioners (media lawyers) and media companies (journalists, editors). Provides structured legal analysis, current case law, and an MCP server for LLM access.

## Scope

- **Legal domain**: Swiss media law / personality rights as core, with DACH comparative references (Germany, Austria)
- **Audience**: Dual — media professionals (plain-language summaries, checklists) and lawyers (academic doctrine, full case law)
- **Languages**: German (primary) + English (international access, ECHR context)
- **Update cadence**: Daily automated via GitHub Actions, quality-gated by evaluator agent
- **Access model**: Open access website + MCP server for LLM integration

## Architecture Overview

Fork & Adapt from Open Legal Commentary. Same proven stack (Astro + Python pipeline + MCP + GitHub Actions), but restructured from per-article to per-topic organization.

```
Medienrechtspraxis/
  content/                  # Generated content (topic-based)
  agents/                   # Python pipeline (generate, evaluate, translate)
  guidelines/               # Quality standards + topic-specific context
  site/                     # Astro static site
  mcp-server/               # MCP server for LLM access
  scripts/                  # Data fetching, article texts, bootstrapping
  .github/workflows/        # CI/CD: daily update, build, deploy
```

---

## 1. Content Model

### 1.1 Topic-Based Structure

Content is organized by legal topic, not by statute article. Each topic is a directory:

```
content/
  persoenlichkeitsschutz/
    meta.yaml
    summary.md
    doctrine.md
    caselaw.md
    summary.en.md
    doctrine.en.md
    caselaw.en.md
  gegendarstellung/
  quellenschutz/
  bildnisschutz/
  ehrverletzung/
  lauterkeitsrecht-medien/
  datenschutz-medien/
  online-medien/
  pressefreiheit/
  recht-am-eigenen-bild/
  werbung-sponsoring/
  urheberrecht-medien/
  rundfunkrecht/
```

### 1.2 Topic Metadata (meta.yaml)

```yaml
title:
  de: "Persönlichkeitsschutz"
  en: "Protection of Personality Rights"
slug: persoenlichkeitsschutz
description:
  de: "Zivilrechtlicher Schutz der Persönlichkeit gegen Medienberichterstattung"
  en: "Civil law protection of personality against media reporting"
related_articles:
  - law: ZGB
    articles: ["28", "28a", "28b", "28c", "28d", "28e", "28f", "28g", "28h", "28i", "28k", "28l"]
  - law: EMRK
    articles: ["8", "10"]
  - law: BV
    articles: ["10", "13", "17"]
dach_references:
  - jurisdiction: DE
    laws: ["BGB §823", "BGB §1004", "KUG §22-23"]
  - jurisdiction: AT
    laws: ["ABGB §16", "MedienG §6-8"]
layers:
  summary: { status: published, updated: "2026-03-26" }
  doctrine: { status: published, updated: "2026-03-26" }
  caselaw: { status: published, updated: "2026-03-26" }
tags: ["privacy", "personality-rights", "injunction"]
sort_order: 1
```

### 1.3 Three Content Layers

**Summary** (for media professionals):
- Plain language, 300-500 words
- Practical orientation: "What can I do? What are the risks?"
- Checklist-style guidance where applicable
- No footnotes, no Randziffern
- Key case references as inline links only

**Doctrine** (for lawyers):
- Academic analysis with Randziffern (N. 1, N. 2, ...)
- DACH comparative sections where relevant
- Minimum 5 cited sources (BGE, doctrine, Botschaft)
- Structured: Legal basis → Requirements → Legal consequences → DACH comparison → Practical implications
- 1500-3000 words per topic

**Caselaw** (for both):
- Current case law digest, thematically grouped
- Courts covered: BGer, EGMR, UBI, cantonal instances
- Per decision: citation, date, one-paragraph summary, significance rating
- Chronological within groups, most recent first
- Updated daily when new relevant decisions appear

---

## 2. Content Pipeline

### 2.1 Architecture

```
agents/
  pipeline.py              # Orchestrator: bootstrap, daily-update, regenerate
  generation.py            # Topic agent: generates layers with MCP tools
  evaluator.py             # Quality gate: checks against media law rubric
  translator.py            # DE → EN translation
  anthropic_client.py      # Anthropic Messages API client (reused from OLC)
  mcp_client.py            # Streamable HTTP MCP client (reused from OLC)
  tools/
    opencaselaw.py         # BGer/EGMR decisions via opencaselaw MCP
    legislation.py         # Statute text retrieval
```

### 2.2 Generation Flow

Per topic, per layer:

1. Build system prompt from `guidelines/global.md` + `guidelines/{topic}.md` + linked statute texts from `meta.yaml`
2. Topic agent generates layer with MCP tool access (`search_decisions`, `find_leading_cases`, `get_doctrine`, `get_commentary`)
3. Evaluator checks against `guidelines/evaluate.md` — 5 non-negotiables + 5 scored dimensions
4. Pass → Translator generates EN version → write to `content/{topic}/`
5. Fail → retry with evaluator feedback (max 3 attempts) → if still fails, flag for manual review

### 2.3 Daily Update Flow

Executed by GitHub Actions cron job (nightly):

1. Query opencaselaw MCP: new decisions since last run
2. Filter: media-law-relevant decisions (keyword matching + article mapping from `meta.yaml`)
3. For each affected topic: regenerate caselaw layer
4. If new leading case detected: cascade to doctrine + summary regeneration
5. Evaluator gate on all regenerated layers
6. Auto-commit passing content, deploy site
7. Log: updated topics, new decisions found, cost

### 2.4 Bootstrap Flow

Initial content generation for all topics:

```bash
uv run python -m agents.pipeline bootstrap --topic persoenlichkeitsschutz
uv run python -m agents.pipeline bootstrap --all --max-budget 100
uv run python -m agents.pipeline bootstrap --state-file state.json  # resume
```

### 2.5 Guidelines

```
guidelines/
  global.md                        # Cross-cutting quality standards
  evaluate.md                      # Evaluation rubric
  persoenlichkeitsschutz.md        # Topic-specific: key cases, debates, DACH specifics
  quellenschutz.md
  gegendarstellung.md
  bildnisschutz.md
  ehrverletzung.md
  datenschutz-medien.md
  online-medien.md
  pressefreiheit.md
  ...
```

**global.md** covers:
- Academic excellence standards
- Citation format (BGE, EGMR, German/Austrian courts)
- DACH comparison requirements
- Layer-specific formatting rules
- Tone: authoritative but accessible

**evaluate.md** covers:
- 5 non-negotiables (any fail = reject): factual accuracy, correct citations, no hallucinated cases, proper DACH attribution, language quality
- 5 scored dimensions (threshold: 3/5 each): depth, completeness, practical value, source quality, readability

---

## 3. Site Architecture

### 3.1 Tech Stack

- **Framework**: Astro 4.x (static site generation)
- **Search**: Pagefind (client-side, post-build)
- **Styling**: CSS (no framework, custom design)
- **Languages**: TypeScript
- **Deploy**: GitHub Pages via GitHub Actions

### 3.2 Directory Structure

```
site/
  src/
    layouts/
      BaseLayout.astro            # HTML shell, nav, footer
      TopicLayout.astro           # Topic page with tab navigation
    pages/
      de/
        index.astro               # Homepage: recent updates + topic overview
        [topic].astro             # Dynamic topic page
        about.astro               # About the project
        methodology.astro         # How content is generated
      en/
        index.astro
        [topic].astro
        about.astro
        methodology.astro
    components/
      TopicCard.astro             # Topic tile for overview grid
      LayerTabs.astro             # Praxis | Doktrin | Rechtsprechung tabs
      CaselawTimeline.astro       # Chronological decision display
      DachComparison.astro        # CH/DE/AT comparison box
      SearchBar.astro             # Pagefind integration
      RelatedArticles.astro       # Linked statute articles list
      RecentUpdates.astro         # "Latest updates" feed
      Checklist.astro             # Practice checklists in summary layer
      LanguageSwitcher.astro      # DE/EN toggle
    lib/
      content.ts                  # Content loader from content/
      i18n.ts                     # DE/EN string translations
      topics.ts                   # Topic metadata, sorting, tag handling
  public/
    favicon.svg
    og-image.png
  astro.config.mjs
  package.json
```

### 3.3 Pages

**Homepage** (`/de/`, `/en/`):
- Hero: project title + one-line description
- "Letzte Aktualisierungen" — feed of recent decisions/changes with dates
- Topic grid: cards sorted by last update, showing title + short description + tags
- Search bar (Pagefind)

**Topic Page** (`/de/{topic}`, `/en/{topic}`):
- Title + description
- Tab navigation: Praxis | Doktrin | Rechtsprechung
- Auto-generated TOC from headings
- Sidebar: related statute articles (linked), DACH references, tags
- Randziffern anchors (N. 1 deep-links)
- BGE/EGMR citation links
- Reading progress bar, back-to-top button
- "Last updated" timestamp per layer

**About** (`/de/about`, `/en/about`):
- Project description, team, open-access commitment
- Link to GitHub repo, MCP server documentation

**Methodology** (`/de/methodology`, `/en/methodology`):
- How content is AI-generated
- Quality assurance process (evaluator)
- Update frequency and sources
- Transparency about limitations

### 3.4 Search

- Pagefind: full-text client-side search, index built post-build
- Filters: topic, language, date range
- Results show topic title + matched excerpt + layer indicator

### 3.5 Design Principles

- Clean, professional, law-firm-appropriate aesthetic
- High readability: generous whitespace, clear typography
- Mobile-responsive
- Fast: static site, no client-side framework overhead
- Accessible: semantic HTML, ARIA labels, keyboard navigation

---

## 4. MCP Server

### 4.1 Purpose

Expose Medienrechtspraxis content to LLMs via the Model Context Protocol. Enables AI assistants to answer media law questions grounded in structured, current legal analysis.

### 4.2 Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `search_topics` | Full-text search across all topic chapters | `query`, `lang`, `tags` |
| `get_topic` | Get full content of a topic layer | `topic_slug`, `layer` (summary/doctrine/caselaw), `lang` |
| `search_caselaw` | Search case law digests | `query`, `court`, `date_from`, `date_to` |
| `get_recent_updates` | Latest N content updates | `limit`, `lang` |
| `check_publication_risk` | Given a publication scenario, return relevant legal topics + key rules | `scenario_description`, `lang` |
| `get_dach_comparison` | CH/DE/AT comparison for a topic | `topic_slug`, `lang` |

### 4.3 Architecture

```
mcp-server/
  src/
    server.ts                  # MCP protocol handler (Streamable HTTP + SSE)
    tools/
      search_topics.ts
      get_topic.ts
      search_caselaw.ts
      recent_updates.ts
      publication_risk.ts
      dach_comparison.ts
    lib/
      content_loader.ts        # Reads content/ from build artifacts
      search_index.ts          # Pre-built search index
  package.json
  tsconfig.json
```

### 4.4 Data Source

The MCP server reads the same `content/` directory that feeds the site. At each site deploy, the content is bundled for the MCP server. No separate database required.

### 4.5 Deployment

Cloudflare Worker or standalone Node.js service. Endpoint: `mcp.medienrechtspraxis.ch/` (or similar).

### 4.6 `check_publication_risk` — Key Feature

This tool is designed for the primary use case: a journalist or editor asks their AI assistant "Can I publish this?" The tool:

1. Takes a free-text scenario description
2. Matches against topic tags and content
3. Returns relevant topic summaries + key legal rules + risk indicators
4. Does NOT give legal advice — points to the relevant analysis and flags risks

---

## 5. CI/CD & GitHub Actions

### 5.1 Workflows

**daily-update.yml** (cron: 0 5 * * *):
1. Run Python pipeline: check for new decisions, update affected topics
2. Auto-commit content changes
3. Trigger site build if content changed

**build-site.yml** (on push to content/ or site/):
1. Install dependencies (uv for Python, npm for Astro)
2. Build Astro site
3. Run Pagefind indexer
4. Deploy to GitHub Pages

**deploy-mcp.yml** (on push to mcp-server/ or content/):
1. Bundle content for MCP server
2. Build and deploy MCP server (Cloudflare Worker or similar)

### 5.2 Branch Strategy

- `main`: production, auto-deploys
- Feature branches for manual development
- Daily update commits go directly to `main` (quality-gated by evaluator)

---

## 6. Dependencies & Tooling

### 6.1 Python (Pipeline)

- Python 3.12+, managed with `uv`
- `anthropic` — Claude API
- `httpx` — async HTTP for MCP calls
- `pydantic` — data validation
- `pyyaml` — metadata

### 6.2 Node.js (Site + MCP Server)

- Astro 4.x
- Pagefind
- TypeScript

### 6.3 External Services

- **Anthropic API** — content generation + evaluation + translation
- **opencaselaw MCP** (`mcp.opencaselaw.ch`) — Swiss case law, legislation, doctrine
- **GitHub Pages** — site hosting
- **Cloudflare Workers** (or alternative) — MCP server hosting

---

## 7. Initial Topic List

Priority order for bootstrap:

1. **Persönlichkeitsschutz** — Art. 28 ZGB ff., core of media law
2. **Gegendarstellung** — Art. 28g-l ZGB, high practical relevance
3. **Quellenschutz** — Art. 17 BV, Art. 28a StPO, journalist privilege
4. **Ehrverletzung** — Art. 173-177 StGB, defamation
5. **Bildnisschutz / Recht am eigenen Bild** — personality + copyright intersection
6. **Pressefreiheit** — Art. 17 BV, Art. 10 EMRK, constitutional framework
7. **Datenschutz & Medien** — DSG Medienprivileg, DSGVO Art. 85
8. **Online-Medien & Plattformhaftung** — DSA, E-Commerce, social media
9. **Urheberrecht & Medien** — URG Zitatrecht, Embedding, AI-generated content
10. **Lauterkeitsrecht** — UWG media-relevant provisions
11. **Rundfunkrecht** — RTVG, UBI practice
12. **Werbung & Sponsoring** — RTVG, UWG, Influencer-Recht

---

## 8. Non-Goals (v1)

- No user accounts or login
- No commenting system
- No real-time notifications
- No paid tier
- No legal advice disclaimer beyond methodology page
- No French/Italian translations (EN sufficient for international reach)
- No custom CMS — content managed via git + pipeline
