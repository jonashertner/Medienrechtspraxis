#!/usr/bin/env bash
# bootstrap.sh — Set up the project from scratch
set -euo pipefail

echo "═══════════════════════════════════════════"
echo "  Medienrechtspraxis — Project Bootstrap"
echo "═══════════════════════════════════════════"
echo ""

# Check prerequisites
command -v uv >/dev/null 2>&1 || { echo "❌ uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "❌ Node.js not found. Install Node.js 20+"; exit 1; }

# Check API key
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
  fi
  if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    echo "❌ ANTHROPIC_API_KEY not set. Copy .env.example to .env and fill in your key."
    exit 1
  fi
fi

echo "✓ Prerequisites OK"
echo ""

# Install Python dependencies
echo "📦 Installing Python dependencies..."
uv sync
echo ""

# Generate meta.yaml for all topics
echo "📝 Generating topic metadata..."
uv run python scripts/generate_meta.py
echo ""

# Install site dependencies
echo "📦 Installing site dependencies..."
cd site && npm install && cd ..
echo ""

# Install MCP server dependencies
echo "📦 Installing MCP server dependencies..."
cd mcp-server && npm install && cd ..
echo ""

echo "═══════════════════════════════════════════"
echo "  ✓ Setup complete!"
echo ""
echo "  Next steps:"
echo "    1. Bootstrap content (single topic):"
echo "       uv run python -m agents.pipeline bootstrap --topic persoenlichkeitsschutz"
echo ""
echo "    2. Bootstrap all content (costs ~\$50-100):"
echo "       uv run python -m agents.pipeline bootstrap --all --max-budget 100"
echo ""
echo "    3. Run site locally:"
echo "       cd site && npm run dev"
echo ""
echo "    4. Run MCP server locally:"
echo "       cd mcp-server && npm run dev"
echo "═══════════════════════════════════════════"
