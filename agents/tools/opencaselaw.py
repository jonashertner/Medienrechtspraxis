"""Wrappers around opencaselaw MCP tools for the content pipeline."""

from __future__ import annotations

import logging
from typing import Any

from agents.mcp_client import MCPClient

logger = logging.getLogger(__name__)


async def search_decisions(
    mcp: MCPClient,
    *,
    query: str,
    language: str = "de",
    court: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Search Swiss court decisions via opencaselaw MCP."""
    args: dict[str, Any] = {"query": query, "language": language, "limit": limit}
    if court:
        args["court"] = court
    if date_from:
        args["date_from"] = date_from
    if date_to:
        args["date_to"] = date_to

    result = await mcp.call_tool("search_decisions", args)
    if isinstance(result, dict) and "decisions" in result:
        return result["decisions"]
    if isinstance(result, list):
        return result
    return []


async def find_leading_cases(
    mcp: MCPClient,
    *,
    topic: str,
    language: str = "de",
    limit: int = 10,
) -> list[dict]:
    """Find the most-cited decisions for a topic."""
    result = await mcp.call_tool("find_leading_cases", {
        "query": topic,
        "language": language,
        "limit": limit,
    })
    if isinstance(result, dict) and "decisions" in result:
        return result["decisions"]
    if isinstance(result, list):
        return result
    return []


async def get_doctrine(
    mcp: MCPClient,
    *,
    article: str,
    law: str = "ZGB",
    language: str = "de",
) -> dict | None:
    """Get leading cases and doctrine for a statute article."""
    result = await mcp.call_tool("get_doctrine", {
        "article": article,
        "law": law,
        "language": language,
    })
    return result if isinstance(result, dict) else None


async def get_commentary(
    mcp: MCPClient,
    *,
    article: str,
    law: str = "ZGB",
    language: str = "de",
) -> dict | None:
    """Look up scholarly commentary from OnlineKommentar.ch."""
    result = await mcp.call_tool("get_commentary", {
        "article": article,
        "law": law,
        "language": language,
    })
    return result if isinstance(result, dict) else None


async def get_law(
    mcp: MCPClient,
    *,
    law: str,
    language: str = "de",
) -> dict | None:
    """Look up a Swiss federal law by SR number or abbreviation."""
    result = await mcp.call_tool("get_law", {
        "law": law,
        "language": language,
    })
    return result if isinstance(result, dict) else None


async def get_decision(
    mcp: MCPClient,
    *,
    decision_id: str,
) -> dict | None:
    """Fetch a single court decision with full text."""
    result = await mcp.call_tool("get_decision", {
        "decision_id": decision_id,
    })
    return result if isinstance(result, dict) else None


async def search_commentaries(
    mcp: MCPClient,
    *,
    query: str,
    language: str = "de",
    limit: int = 10,
) -> list[dict]:
    """Full-text search across OnlineKommentar.ch commentaries."""
    result = await mcp.call_tool("search_commentaries", {
        "query": query,
        "language": language,
        "limit": limit,
    })
    if isinstance(result, dict) and "commentaries" in result:
        return result["commentaries"]
    if isinstance(result, list):
        return result
    return []
