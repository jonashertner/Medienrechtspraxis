"""Anthropic Messages API client with cost tracking and retry logic."""

import os
from dataclasses import dataclass, field

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential


@dataclass
class UsageTracker:
    """Track API usage and costs across pipeline runs."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    calls: int = 0

    # Approximate pricing per million tokens (Claude Sonnet 4)
    INPUT_COST_PER_M: float = 3.0
    OUTPUT_COST_PER_M: float = 15.0
    CACHE_READ_COST_PER_M: float = 0.30
    CACHE_WRITE_COST_PER_M: float = 3.75

    @property
    def estimated_cost_usd(self) -> float:
        return (
            self.input_tokens * self.INPUT_COST_PER_M / 1_000_000
            + self.output_tokens * self.OUTPUT_COST_PER_M / 1_000_000
            + self.cache_read_tokens * self.CACHE_READ_COST_PER_M / 1_000_000
            + self.cache_write_tokens * self.CACHE_WRITE_COST_PER_M / 1_000_000
        )

    def record(self, usage: anthropic.types.Usage) -> None:
        self.input_tokens += usage.input_tokens
        self.output_tokens += usage.output_tokens
        self.cache_read_tokens += getattr(usage, "cache_read_input_tokens", 0) or 0
        self.cache_write_tokens += getattr(usage, "cache_creation_input_tokens", 0) or 0
        self.calls += 1


@dataclass
class AnthropicClient:
    """Wrapper around the Anthropic Messages API."""

    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 8192
    usage: UsageTracker = field(default_factory=UsageTracker)
    _client: anthropic.Anthropic | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        self._client = anthropic.Anthropic(api_key=api_key)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30))
    def generate(
        self,
        *,
        system: str,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int | None = None,
    ) -> str:
        """Generate a completion. Returns the text content."""
        response = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens or self.max_tokens,
            temperature=temperature,
            system=system,
            messages=messages,
        )
        self.usage.record(response.usage)
        return response.content[0].text

    def check_budget(self, max_budget_usd: float) -> bool:
        """Return True if still within budget."""
        return self.usage.estimated_cost_usd < max_budget_usd
