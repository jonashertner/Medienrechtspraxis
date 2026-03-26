.PHONY: setup bootstrap bootstrap-all validate site mcp dev lint clean

# Initial project setup
setup:
	bash scripts/bootstrap.sh

# Bootstrap single topic
bootstrap:
	uv run python -m agents.pipeline bootstrap --topic $(TOPIC)

# Bootstrap all topics
bootstrap-all:
	uv run python -m agents.pipeline bootstrap --all --max-budget $(or $(BUDGET),100) --state-file state.json

# Run daily update
update:
	uv run python -m agents.pipeline daily-update

# Validate content
validate:
	uv run python scripts/validate_content.py

# Run site locally
site:
	cd site && npm run dev

# Run MCP server locally
mcp:
	cd mcp-server && npm run dev

# Build site for production
build-site:
	cd site && npm run build

# Build MCP server
build-mcp:
	cd mcp-server && npm run build

# Lint Python code
lint:
	uv run ruff check agents/ scripts/
	uv run ruff format --check agents/ scripts/

# Format Python code
format:
	uv run ruff format agents/ scripts/

# Clean build artifacts
clean:
	rm -rf site/dist site/.astro mcp-server/dist state.json
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Docker: build and run MCP server
docker-mcp:
	docker compose up --build
