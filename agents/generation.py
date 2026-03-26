"""Topic agent: generates content layers using Claude + MCP tools."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from agents.anthropic_client import AnthropicClient
from agents.mcp_client import MCPClient
from agents.tools.legislation import get_statute_texts
from agents.tools.opencaselaw import (
    find_leading_cases,
    get_commentary,
    get_doctrine,
    search_commentaries,
    search_decisions,
)

logger = logging.getLogger(__name__)

CONTENT_DIR = Path("content")
GUIDELINES_DIR = Path("guidelines")

LAYER_SPECS = {
    "summary": {
        "description": "Plain-language summary for media professionals (300-500 words)",
        "filename": "summary.md",
    },
    "doctrine": {
        "description": "Academic legal analysis with Randziffern for lawyers (1500-3000 words)",
        "filename": "doctrine.md",
    },
    "caselaw": {
        "description": "Current case law digest, thematically grouped",
        "filename": "caselaw.md",
    },
}


@dataclass
class TopicContext:
    """All context needed to generate a topic layer."""

    slug: str
    meta: dict
    global_guidelines: str
    topic_guidelines: str | None
    statute_texts: dict[str, str]
    leading_cases: list[dict]
    commentaries: list[dict]
    doctrine_refs: list[dict | None]
    recent_decisions: list[dict]


async def gather_topic_context(
    slug: str,
    mcp: MCPClient,
) -> TopicContext:
    """Gather all MCP data and guidelines for a topic."""
    topic_dir = CONTENT_DIR / slug
    meta_path = topic_dir / "meta.yaml"

    with open(meta_path) as f:
        meta = yaml.safe_load(f)

    # Load guidelines
    global_path = GUIDELINES_DIR / "global.md"
    global_guidelines = global_path.read_text() if global_path.exists() else ""

    topic_guidelines_path = GUIDELINES_DIR / f"{slug}.md"
    topic_guidelines = (
        topic_guidelines_path.read_text() if topic_guidelines_path.exists() else None
    )

    # Fetch statute texts
    related_articles = meta.get("related_articles", [])
    statute_texts = await get_statute_texts(mcp, related_articles=related_articles)

    # Fetch leading cases
    title_de = meta.get("title", {}).get("de", slug)
    leading = await find_leading_cases(mcp, topic=title_de, limit=15)

    # Fetch commentaries for primary law articles
    commentaries = []
    for entry in related_articles[:1]:  # Primary law only
        for article in entry.get("articles", [])[:3]:  # Top 3 articles
            c = await get_commentary(mcp, article=article, law=entry["law"])
            if c:
                commentaries.append(c)

    # Fetch doctrine references
    doctrine_refs = []
    for entry in related_articles[:1]:
        for article in entry.get("articles", [])[:3]:
            d = await get_doctrine(mcp, article=article, law=entry["law"])
            if d:
                doctrine_refs.append(d)

    # Fetch recent decisions
    recent = await search_decisions(mcp, query=title_de, limit=20)

    # Also search commentaries for additional context
    comm_search = await search_commentaries(mcp, query=title_de, limit=5)
    commentaries.extend(comm_search)

    return TopicContext(
        slug=slug,
        meta=meta,
        global_guidelines=global_guidelines,
        topic_guidelines=topic_guidelines,
        statute_texts=statute_texts,
        leading_cases=leading,
        commentaries=commentaries,
        doctrine_refs=doctrine_refs,
        recent_decisions=recent,
    )


def build_system_prompt(ctx: TopicContext, layer: str) -> str:
    """Build the system prompt for content generation."""
    spec = LAYER_SPECS[layer]
    title_de = ctx.meta.get("title", {}).get("de", ctx.slug)

    parts = [
        f"You are an expert legal commentator writing about Swiss media law.",
        f"You are generating the **{layer}** layer for the topic: **{title_de}**.",
        f"Layer specification: {spec['description']}.",
        "",
        "# Quality Standards",
        ctx.global_guidelines,
    ]

    if ctx.topic_guidelines:
        parts.extend(["", "# Topic-Specific Guidelines", ctx.topic_guidelines])

    # Add statute texts
    if ctx.statute_texts:
        parts.append("\n# Relevant Statute Texts")
        for key, text in ctx.statute_texts.items():
            parts.append(f"\n## {key}\n{text}")

    # Add leading cases
    if ctx.leading_cases:
        parts.append("\n# Leading Cases (Leitentscheide)")
        for case in ctx.leading_cases[:10]:
            parts.append(f"- {json.dumps(case, ensure_ascii=False)}")

    # Add commentaries
    if ctx.commentaries:
        parts.append("\n# Available Commentaries")
        for c in ctx.commentaries[:5]:
            parts.append(f"- {json.dumps(c, ensure_ascii=False)}")

    # Add doctrine references
    if ctx.doctrine_refs:
        parts.append("\n# Doctrine References")
        for d in ctx.doctrine_refs[:5]:
            if d:
                parts.append(f"- {json.dumps(d, ensure_ascii=False)}")

    # Layer-specific instructions
    if layer == "summary":
        parts.extend([
            "\n# Output Instructions",
            "Write in German. Plain language, no footnotes, no Randziffern.",
            "300-500 words. Practical orientation: what can journalists/editors do?",
            "Include a checklist where applicable.",
            "Key case references as inline mentions only (e.g., 'gemäss BGE 127 III 481').",
            "Format as Markdown. Start with a ## heading for the topic title.",
        ])
    elif layer == "doctrine":
        parts.extend([
            "\n# Output Instructions",
            "Write in German. Academic register with Randziffern (N. 1, N. 2, ...).",
            "1500-3000 words. Minimum 5 cited sources (BGE, doctrine, Botschaft).",
            "Structure: Legal basis → Requirements → Legal consequences → DACH comparison → Practical implications.",
            "Include DACH comparative sections for DE and AT where relevant.",
            "Format as Markdown. Use ## for main sections, ### for subsections.",
            "Citation format: BGE 127 III 481, Urteil 5A_xxx/20xx, EGMR Nr. xxx.",
        ])
    elif layer == "caselaw":
        parts.extend([
            "\n# Output Instructions",
            "Write in German. Case law digest format.",
            "Group thematically. Within groups, order chronologically (most recent first).",
            "Per decision: citation, date, one-paragraph summary, significance rating (★ to ★★★).",
            "Courts: BGer, EGMR, UBI, cantonal instances.",
            "Format as Markdown with ## for thematic groups.",
        ])

    # Add recent decisions for caselaw layer
    if layer == "caselaw" and ctx.recent_decisions:
        parts.append("\n# Recent Decisions to Include")
        for d in ctx.recent_decisions:
            parts.append(f"- {json.dumps(d, ensure_ascii=False)}")

    return "\n".join(parts)


async def generate_layer(
    client: AnthropicClient,
    ctx: TopicContext,
    layer: str,
) -> str:
    """Generate a single content layer for a topic."""
    system = build_system_prompt(ctx, layer)
    title_de = ctx.meta.get("title", {}).get("de", ctx.slug)

    user_message = (
        f"Generate the {layer} layer for '{title_de}'. "
        f"Follow all quality standards and formatting instructions precisely. "
        f"Output only the Markdown content, no preamble."
    )

    content = client.generate(
        system=system,
        messages=[{"role": "user", "content": user_message}],
        temperature=0.3,
    )

    return content


def write_layer(slug: str, layer: str, content: str, lang: str = "de") -> Path:
    """Write generated content to the appropriate file."""
    topic_dir = CONTENT_DIR / slug
    topic_dir.mkdir(parents=True, exist_ok=True)

    spec = LAYER_SPECS[layer]
    filename = spec["filename"]
    if lang != "de":
        filename = filename.replace(".md", f".{lang}.md")

    path = topic_dir / filename
    path.write_text(content, encoding="utf-8")
    logger.info("Wrote %s (%d chars)", path, len(content))
    return path
