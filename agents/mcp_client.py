"""Streamable HTTP MCP client for opencaselaw and other MCP servers."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

MCP_DEFAULT_URL = "https://mcp.opencaselaw.ch"


@dataclass
class MCPClient:
    """Client for MCP servers using Streamable HTTP transport."""

    base_url: str = MCP_DEFAULT_URL
    _http: httpx.AsyncClient | None = field(default=None, repr=False)
    _session_id: str | None = field(default=None, repr=False)
    _request_id: int = field(default=0, repr=False)

    async def __aenter__(self) -> "MCPClient":
        self._http = httpx.AsyncClient(timeout=60.0)
        await self._initialize()
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._http:
            await self._http.aclose()

    async def _initialize(self) -> dict:
        """Send MCP initialize request."""
        result = await self._send_request("initialize", {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "medienrechtspraxis-pipeline", "version": "0.1.0"},
        })
        # Send initialized notification
        await self._send_notification("notifications/initialized")
        return result

    async def call_tool(self, name: str, arguments: dict | None = None) -> Any:
        """Call an MCP tool and return the result."""
        result = await self._send_request("tools/call", {
            "name": name,
            "arguments": arguments or {},
        })
        if not result or "content" not in result:
            return None
        # Extract text content from MCP tool result
        texts = []
        for block in result["content"]:
            if block.get("type") == "text":
                text = block.get("text", "")
                try:
                    texts.append(json.loads(text))
                except (json.JSONDecodeError, TypeError):
                    texts.append(text)
        return texts[0] if len(texts) == 1 else texts

    async def list_tools(self) -> list[dict]:
        """List available MCP tools."""
        result = await self._send_request("tools/list", {})
        return result.get("tools", []) if result else []

    async def _send_request(self, method: str, params: dict) -> dict | None:
        """Send a JSON-RPC request over Streamable HTTP."""
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params,
        }
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id

        resp = await self._http.post(self.base_url, json=payload, headers=headers)
        resp.raise_for_status()

        # Capture session ID from response
        if "mcp-session-id" in resp.headers:
            self._session_id = resp.headers["mcp-session-id"]

        data = resp.json()
        if "error" in data:
            logger.error("MCP error: %s", data["error"])
            return None
        return data.get("result")

    async def _send_notification(self, method: str, params: dict | None = None) -> None:
        """Send a JSON-RPC notification (no response expected)."""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
        }
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id

        await self._http.post(self.base_url, json=payload, headers=headers)
