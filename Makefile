.PHONY: setup data schemas test lint eval-replay eval-live demo-1 demo-2 demo-red verify report mcp site

setup:
	uv sync --extra dev
	uv run python scripts/generate_synthetic_data.py
	uv run python scripts/build_knowledge_index.py
	uv run python scripts/export_schemas.py

data:
	uv run python scripts/generate_synthetic_data.py
	uv run python scripts/build_knowledge_index.py
	uv run financial-controller validate

schemas:
	uv run python scripts/export_schemas.py

test:
	uv run pytest -m "not live and not demo_red"

lint:
	uv run ruff check .

eval-replay:
	uv run financial-controller eval --mode replay

eval-live:
	uv run financial-controller eval --mode live

demo-1:
	uv run financial-controller run --case annual-software-prepaid --mode live

demo-2:
	uv run financial-controller run --case unmatched-receipts --mode replay

demo-red:
	uv run pytest -m demo_red tests/demo_red

report:
	uv run financial-controller report --latest

mcp:
	uv run financial-controller-mcp

site:
	uv run financial-controller site

verify:
	uv lock --check
	uv run python scripts/generate_synthetic_data.py --check
	uv run python scripts/build_knowledge_index.py --check
	uv run ruff check .
	uv run pytest -m "not live and not demo_red"
	uv run financial-controller eval --mode replay
