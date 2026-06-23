# Repository Guidelines

## Project Structure & Module Organization

The repository combines implementation code with planning and progress documents:

- `app.py`: Streamlit application entry point.
- `src/scm/`: simulation, CSV import, classification, safety-stock, strategy comparison, database, and diagnosis modules.
- `tests/`: pytest unit, integration, and Streamlit smoke tests.
- `scripts/init_db.py`: reproducible SQLite/sample-data initialization.
- `Plan.md`: product history and research.
- `readme.md`: development order and module responsibilities.
- `checklist.md`: the source of truth for task progress.

Keep generated `data/scm.db` local. Preserve the eight module boundaries from `readme.md`. Do not add the excluded demand-forecasting or Fisher Map modules without updating both planning documents.

## Build, Test, and Development Commands

Use `uv` from the repository root:

```powershell
uv sync --all-groups
uv run python scripts/init_db.py --replace
uv run streamlit run app.py
uv run pytest -q
uv run ruff check .
```

The first command creates `.venv` from `pyproject.toml` and `uv.lock`. The second recreates deterministic sample data. Commands must work from the repository root.

## Coding Style & Naming Conventions

Target Python 3.11 or newer and follow PEP 8 with four-space indentation. Use `snake_case` for modules, functions, and variables; `PascalCase` for classes; and `UPPER_SNAKE_CASE` for constants. Add type hints to public functions and concise docstrings where formulas or SCM assumptions are not obvious. Keep calculations separate from Streamlit rendering. Ruff enforces imports, common bugs, modernization, and a 100-character line limit.

## Testing Guidelines

Use `pytest`; name files `test_<module>.py` and tests `test_<behavior>()`. Cover classification boundaries, scenario monotonicity, zero and constrained budgets, allocation totals, API fallback, and the 20%-budget comparison. Tests must use deterministic fixtures or fixed random seeds. No numeric coverage gate exists yet, but every bug fix requires a regression test.

## Commit & Pull Request Guidelines

There is no SCM-specific Git history to infer conventions from. Use short imperative commits with prefixes such as `feat:`, `fix:`, `test:`, and `docs:`. Pull requests should explain the affected module, calculation changes, validation performed, and checklist updates. Include screenshots for Streamlit UI changes and link related issues when available.

## Security & Configuration

Never commit OpenAI API keys, `.env` files, customer data, or generated databases. Keep the demo mode functional when API credentials or credits are unavailable, and clearly label simulated data in outputs. Treat files under `csv/` as public synthetic fixtures only.
