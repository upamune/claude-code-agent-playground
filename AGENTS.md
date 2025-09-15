# Repository Guidelines

## Project Structure & Module Organization
- `agents/`: Example agents under `examples/`, each with `main.py` (e.g., `hello_claude/`, `calculator/`, `streaming_input/`, `continuing_conversation/`, `advanced_permission_control/`, `hooks/`, `using_interrupts/`).
- `.claude/`: Agent definitions and helper command docs (`agents/`, `commands/`).
- `docs/`: Reference materials (`claude/`, `claude_code/`, `claude_code_sdk/`, `python/`).
- `scripts/`: Utilities such as `fetch_doc.py` for fetching and converting pages to Markdown.
- `tests/`: Place new tests here; name files `test_*.py`.
- `mise.toml`: Tool pinning (e.g., Bun via `mise`).

## Build, Test, and Development Commands
- Run any example: `uv run --script agents/examples/<name>/main.py` (e.g., `agents/examples/hello_claude/main.py`).
- Direct execute (if executable): `./agents/examples/<name>/main.py`.
- Quick demos:
  - Streaming Input: `uv run --script agents/examples/streaming_input/main.py`
  - Calculator: `uv run --script agents/examples/calculator/main.py`
- Fetch a documentation page: `./scripts/fetch_doc.py <URL> [--debug]` or `uv run --script scripts/fetch_doc.py <URL> [--debug]`.
- Prereqs: Python 3.11+ and `uv` in `PATH`. Scripts use PEP 723; `uv` resolves dependencies at runtime.

## Coding Style & Naming Conventions
- Python: 4‑space indents, type hints, module‑level docstrings; prefer early returns over deep nesting.
- Naming: `snake_case` for functions/vars, `CAPS` for constants, module files in `snake_case`.
- Lines ≈ 100 chars; favor small, focused modules and pure functions.
- Markdown: Title‑Case headings, fenced code blocks, relative links within the repo.

## Testing Guidelines
- Framework: `pytest`. Put tests under `tests/` named `test_*.py`.
- Run tests: `pytest -q` (add `-k <pattern>` for quick subsets).
- Prioritize unit tests for I/O helpers and core logic (e.g., calculator operations, streaming_input flow control).
- Keep tests deterministic; avoid network and external service dependencies.

## Commit & Pull Request Guidelines
- Commits follow Conventional Commits (e.g., `feat:`, `fix:`, `docs:`, `chore:`).
- PRs include a clear description, linked issues, run steps, and sample output/screenshots.
- For agents, include usage examples (commands above) and expected outputs.

## Agent‑Specific Tips
- Declare dependencies via a PEP 723 block at the top of runnable scripts.
- Keep prompts/docs current in `.claude/agents/` and command docs in `.claude/commands/`.
- Never commit secrets; use environment variables and local `.env` files (git‑ignored).
- Use `mise.toml` to pin tools; run `mise install` to sync versions locally.
