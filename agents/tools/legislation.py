"""Statute text retrieval via opencaselaw MCP."""

from __future__ import annotations

import logging
from typing import Any

from agents.mcp_client import MCPClient

logger = logging.getLogger(__name__)


async def get_statute_texts(
    mcp: MCPClient,
    *,
    related_articles: list[dict],
    language: str = "de",
) -> dict[str, str]:
    """Fetch statute text for all articles referenced in a topic's meta.yaml.

    Args:
        related_articles: List of dicts from meta.yaml, e.g.
            [{"law": "ZGB", "articles": ["28", "28a"]}]

    Returns:
        Dict mapping "LAW Art. N" to the article text.
    """
    texts: dict[str, str] = {}

    for entry in related_articles:
        law = entry["law"]
        for article in entry.get("articles", []):
            try:
                result = await mcp.call_tool("search_laws", {
                    "query": f"{law} Art. {article}",
                    "language": language,
                    "limit": 1,
                })
                if isinstance(result, dict) and "articles" in result:
                    for art in result["articles"]:
                        key = f"{law} Art. {article}"
                        texts[key] = art.get("text", art.get("content", ""))
                        break
                elif isinstance(result, list) and result:
                    item = result[0]
                    key = f"{law} Art. {article}"
                    if isinstance(item, dict):
                        texts[key] = item.get("text", item.get("content", str(item)))
                    else:
                        texts[key] = str(item)
            except Exception:
                logger.warning("Failed to fetch %s Art. %s", law, article, exc_info=True)

    return texts
