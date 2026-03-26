"""Pipeline orchestrator: bootstrap, daily-update, regenerate."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from agents.anthropic_client import AnthropicClient
from agents.evaluator import evaluate
from agents.generation import (
    CONTENT_DIR,
    LAYER_SPECS,
    TopicContext,
    gather_topic_context,
    generate_layer,
    write_layer,
)
from agents.mcp_client import MCPClient
from agents.translator import translate

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger(__name__)
console = Console()

# All defined topics
ALL_TOPICS = [
    "persoenlichkeitsschutz",
    "gegendarstellung",
    "quellenschutz",
    "ehrverletzung",
    "bildnisschutz",
    "pressefreiheit",
    "datenschutz-medien",
    "online-medien",
    "urheberrecht-medien",
    "lauterkeitsrecht-medien",
    "rundfunkrecht",
    "werbung-sponsoring",
]

LAYERS = ["summary", "doctrine", "caselaw"]
MAX_RETRIES = 3


@dataclass
class PipelineState:
    """Tracks progress for resumable runs."""

    completed: dict[str, list[str]]  # topic -> [layers]
    failed: dict[str, list[str]]
    cost_usd: float
    started_at: str
    last_updated: str

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.__dict__, indent=2))

    @classmethod
    def load(cls, path: Path) -> "PipelineState":
        data = json.loads(path.read_text())
        return cls(**data)

    @classmethod
    def fresh(cls) -> "PipelineState":
        now = datetime.now(timezone.utc).isoformat()
        return cls(completed={}, failed={}, cost_usd=0.0, started_at=now, last_updated=now)


from dataclasses import dataclass


async def generate_topic(
    slug: str,
    client: AnthropicClient,
    mcp: MCPClient,
    state: PipelineState,
    layers: list[str] | None = None,
) -> None:
    """Generate all layers for a single topic."""
    layers = layers or LAYERS
    title = slug.replace("-", " ").title()
    completed_layers = state.completed.get(slug, [])

    console.rule(f"[bold blue]{title}")

    # Gather context from MCP
    console.print(f"  Gathering context for [cyan]{slug}[/]...")
    try:
        ctx = await gather_topic_context(slug, mcp)
    except Exception as e:
        logger.error("Failed to gather context for %s: %s", slug, e)
        state.failed.setdefault(slug, []).extend(layers)
        return

    for layer in layers:
        if layer in completed_layers:
            console.print(f"  [dim]Skipping {layer} (already done)[/]")
            continue

        console.print(f"  Generating [yellow]{layer}[/]...")

        success = False
        for attempt in range(1, MAX_RETRIES + 1):
            # Generate
            try:
                content = await asyncio.to_thread(
                    generate_layer, client, ctx, layer
                )
            except Exception as e:
                logger.error("Generation failed (attempt %d): %s", attempt, e)
                continue

            # Evaluate
            title_de = ctx.meta.get("title", {}).get("de", slug)
            eval_result = await asyncio.to_thread(
                evaluate, client, content, layer, title_de
            )

            if eval_result.passed:
                console.print(f"    ✓ Passed evaluation (attempt {attempt})")
                console.print(f"      Scores: {eval_result.scores}")

                # Write DE version
                write_layer(slug, layer, content, lang="de")

                # Translate and write EN version
                console.print(f"    Translating to EN...")
                try:
                    en_content = await asyncio.to_thread(translate, client, content)
                    write_layer(slug, layer, en_content, lang="en")
                except Exception as e:
                    logger.warning("Translation failed for %s/%s: %s", slug, layer, e)

                success = True
                break
            else:
                console.print(
                    f"    ✗ Failed evaluation (attempt {attempt}/{MAX_RETRIES})"
                )
                console.print(f"      Non-negotiables: {eval_result.non_negotiables}")
                console.print(f"      Scores: {eval_result.scores}")
                if attempt < MAX_RETRIES:
                    console.print(f"      Retrying with feedback...")

        if success:
            state.completed.setdefault(slug, []).append(layer)
        else:
            state.failed.setdefault(slug, []).append(layer)
            console.print(f"    [red]✗ {layer} failed after {MAX_RETRIES} attempts[/]")

        state.cost_usd = client.usage.estimated_cost_usd
        state.last_updated = datetime.now(timezone.utc).isoformat()


async def run_bootstrap(
    topics: list[str],
    max_budget: float,
    state_file: Path | None,
) -> None:
    """Bootstrap content for one or more topics."""
    state = PipelineState.fresh()
    if state_file and state_file.exists():
        state = PipelineState.load(state_file)
        console.print(f"Resuming from state file: {state_file}")

    client = AnthropicClient()
    mcp_url = os.environ.get("OPENCASELAW_MCP_URL", "https://mcp.opencaselaw.ch")

    async with MCPClient(base_url=mcp_url) as mcp:
        for slug in topics:
            if not client.check_budget(max_budget):
                console.print(f"[red]Budget limit reached: ${client.usage.estimated_cost_usd:.2f}[/]")
                break

            await generate_topic(slug, client, mcp, state)

            if state_file:
                state.save(state_file)

    # Summary
    console.rule("[bold green]Pipeline Complete")
    table = Table(title="Results")
    table.add_column("Topic")
    table.add_column("Status")
    table.add_column("Layers")
    for slug in topics:
        completed = state.completed.get(slug, [])
        failed = state.failed.get(slug, [])
        status = "✓" if len(completed) == 3 and not failed else "partial" if completed else "✗"
        table.add_row(slug, status, f"{len(completed)}/3 done, {len(failed)} failed")
    console.print(table)
    console.print(f"Total cost: ${client.usage.estimated_cost_usd:.2f}")
    console.print(f"API calls: {client.usage.calls}")


async def run_daily_update() -> None:
    """Check for new decisions and update affected topics."""
    client = AnthropicClient()
    mcp_url = os.environ.get("OPENCASELAW_MCP_URL", "https://mcp.opencaselaw.ch")
    max_budget = float(os.environ.get("MAX_DAILY_BUDGET_USD", "10.0"))

    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

    async with MCPClient(base_url=mcp_url) as mcp:
        # Search for new decisions since yesterday
        from agents.tools.opencaselaw import search_decisions

        console.print(f"Searching for new decisions since {yesterday}...")
        new_decisions = await search_decisions(
            mcp, query="Medien Persönlichkeit Presse", date_from=yesterday, limit=50
        )
        console.print(f"Found {len(new_decisions)} potentially relevant decisions")

        if not new_decisions:
            console.print("[green]No new decisions found. Nothing to update.[/]")
            return

        # Determine affected topics by matching against meta.yaml tags/articles
        affected_topics = set()
        for slug in ALL_TOPICS:
            meta_path = CONTENT_DIR / slug / "meta.yaml"
            if not meta_path.exists():
                continue
            with open(meta_path) as f:
                meta = yaml.safe_load(f)
            tags = meta.get("tags", [])
            title_de = meta.get("title", {}).get("de", "").lower()
            # Simple keyword matching — in production, use article mapping
            for decision in new_decisions:
                dec_text = json.dumps(decision, ensure_ascii=False).lower()
                if any(tag.lower() in dec_text for tag in tags) or title_de in dec_text:
                    affected_topics.add(slug)
                    break

        if not affected_topics:
            console.print("[green]No topics affected by new decisions.[/]")
            return

        console.print(f"Affected topics: {affected_topics}")

        state = PipelineState.fresh()
        for slug in affected_topics:
            if not client.check_budget(max_budget):
                console.print(f"[red]Daily budget reached[/]")
                break
            # Regenerate caselaw layer (and cascade if leading case)
            await generate_topic(slug, client, mcp, state, layers=["caselaw"])

    console.print(f"Daily update cost: ${client.usage.estimated_cost_usd:.2f}")


# ── CLI ──────────────────────────────────────────────────────────────────────


@click.group()
def cli() -> None:
    """Medienrechtspraxis content pipeline."""


@cli.command()
@click.option("--topic", type=str, help="Single topic slug to bootstrap")
@click.option("--all", "all_topics", is_flag=True, help="Bootstrap all topics")
@click.option("--max-budget", type=float, default=100.0, help="Max budget in USD")
@click.option("--state-file", type=click.Path(), default=None, help="State file for resuming")
def bootstrap(
    topic: str | None,
    all_topics: bool,
    max_budget: float,
    state_file: str | None,
) -> None:
    """Bootstrap content for topics."""
    if topic:
        topics = [topic]
    elif all_topics:
        topics = ALL_TOPICS
    else:
        click.echo("Specify --topic or --all")
        sys.exit(1)

    asyncio.run(run_bootstrap(
        topics=topics,
        max_budget=max_budget,
        state_file=Path(state_file) if state_file else None,
    ))


@cli.command()
def daily_update() -> None:
    """Run the daily update pipeline."""
    asyncio.run(run_daily_update())


if __name__ == "__main__":
    cli()
