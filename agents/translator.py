"""DE → EN translation for content layers."""

from __future__ import annotations

import logging

from agents.anthropic_client import AnthropicClient

logger = logging.getLogger(__name__)

TRANSLATION_SYSTEM = """You are a legal translator specializing in Swiss law.
Translate the following German legal text into English.

Rules:
- Maintain all legal precision and nuance.
- Keep Randziffern numbering (N. 1, N. 2, ...) unchanged.
- Keep Swiss case citations in their original form (e.g., BGE 127 III 481).
- Translate German/Austrian legal terms but keep the original in parentheses on first use.
- Maintain all Markdown formatting exactly.
- Keep the same structure, headings, and organization.
- For DACH comparisons, translate the analysis but keep law references original (e.g., "§ 823 BGB").
- Do not add any commentary or notes — output only the translated Markdown.
- Use British English spelling conventions.
"""


def translate(
    client: AnthropicClient,
    content: str,
) -> str:
    """Translate German content to English."""
    result = client.generate(
        system=TRANSLATION_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"Translate the following to English:\n\n{content}",
        }],
        temperature=0.2,
        max_tokens=8192,
    )
    return result
