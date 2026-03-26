"""Quality evaluator: checks generated content against the media law rubric."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from agents.anthropic_client import AnthropicClient

logger = logging.getLogger(__name__)

EVALUATE_GUIDELINES = Path("guidelines/evaluate.md")


@dataclass
class EvaluationResult:
    """Result of content evaluation."""

    passed: bool
    non_negotiables: dict[str, bool]  # 5 checks, all must pass
    scores: dict[str, int]  # 5 dimensions, 1-5 scale
    feedback: str  # Detailed feedback for retry
    raw: str  # Raw evaluator output


EVALUATION_SYSTEM_PROMPT = """You are a senior Swiss media law expert reviewing AI-generated legal content.
You evaluate content against strict quality standards.

You must output ONLY valid JSON with this exact structure:
{
  "non_negotiables": {
    "factual_accuracy": true/false,
    "correct_citations": true/false,
    "no_hallucinated_cases": true/false,
    "proper_dach_attribution": true/false,
    "language_quality": true/false
  },
  "scores": {
    "depth": 1-5,
    "completeness": 1-5,
    "practical_value": 1-5,
    "source_quality": 1-5,
    "readability": 1-5
  },
  "feedback": "Detailed feedback string explaining issues and how to improve."
}

Non-negotiables: ALL must be true for a pass.
Scores: Each must be >= 3 for a pass.

Be strict. This content will be published as authoritative legal commentary."""


def build_evaluation_prompt(content: str, layer: str, topic_title: str) -> str:
    """Build the user message for evaluation."""
    guidelines = ""
    if EVALUATE_GUIDELINES.exists():
        guidelines = EVALUATE_GUIDELINES.read_text()

    return f"""Evaluate the following {layer} layer for the topic "{topic_title}".

{f"# Evaluation Rubric{chr(10)}{guidelines}" if guidelines else ""}

# Content to Evaluate

```markdown
{content}
```

Evaluate strictly. Output only the JSON result."""


def evaluate(
    client: AnthropicClient,
    content: str,
    layer: str,
    topic_title: str,
) -> EvaluationResult:
    """Evaluate generated content. Returns EvaluationResult."""
    user_msg = build_evaluation_prompt(content, layer, topic_title)

    raw = client.generate(
        system=EVALUATION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
        temperature=0.0,
        max_tokens=2048,
    )

    # Parse JSON from response
    try:
        # Strip markdown code fences if present
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1]
            clean = clean.rsplit("```", 1)[0]
        data = json.loads(clean)
    except json.JSONDecodeError:
        logger.error("Evaluator returned invalid JSON: %s", raw[:200])
        return EvaluationResult(
            passed=False,
            non_negotiables={},
            scores={},
            feedback="Evaluation failed: could not parse evaluator response.",
            raw=raw,
        )

    non_neg = data.get("non_negotiables", {})
    scores = data.get("scores", {})
    feedback = data.get("feedback", "")

    # Check pass conditions
    all_non_neg_pass = all(non_neg.values()) if non_neg else False
    all_scores_pass = all(v >= 3 for v in scores.values()) if scores else False
    passed = all_non_neg_pass and all_scores_pass

    return EvaluationResult(
        passed=passed,
        non_negotiables=non_neg,
        scores=scores,
        feedback=feedback,
        raw=raw,
    )
