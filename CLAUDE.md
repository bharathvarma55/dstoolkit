# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Setup:
```bash
python -m venv .venv
.venv\Scripts\activate   # on Windows; `source .venv/bin/activate` on Mac/Linux
pip install -e ".[dev]"
```

Run the full test suite:
```bash
pytest -q
```

Run a single test:
```bash
pytest tests/test_cleaner.py::test_dedupe_and_missing -q
```

Run the CLI (full pipeline or step-by-step):
```bash
dstk run examples/pipeline.yaml
dstk collect examples/pipeline.yaml -o raw.parquet
dstk clean raw.parquet examples/pipeline.yaml -o clean.parquet
dstk validate clean.parquet examples/pipeline.yaml -o validation.json
dstk report clean.parquet examples/pipeline.yaml --validation validation.json -o report.html   # or .pdf
```

Run the web UI:
```bash
streamlit run src/dstoolkit/webapp/app.py
```
(a saved launch config for this is at `.claude/launch.json`)

No linter or formatter is configured in this repo yet — don't assume `ruff`/`black`/`flake8` exist.

## Architecture

dstoolkit is a data pipeline tool — **collect → clean → validate → report** — exposed through
both a Typer CLI (`dstk`) and a Streamlit dashboard. The core design rule: every stage has
**exactly one implementation**, in `src/dstoolkit/pipeline.py` (`collect_stage`, `clean_stage`,
`validate_stage`, `report_stage`). Both interfaces call these directly; neither re-implements
pipeline logic.

Everything is driven by `PipelineConfig` (`src/dstoolkit/config.py`), a Pydantic model normally
loaded from YAML (see `examples/pipeline.yaml`, `examples/pipeline_db.yaml`). It has four
sections: `source`, `cleaning`, `validation` (a list of rules), `report`.

**Collection** (`collectors/`): `SourceConfig.type` selects one of four collectors
(`file_collector`, `db_collector`, `api_collector`, `web_collector`), each returning a
`CollectionResult` (`collectors/base.py`). Fields for all four source types live flatly on one
`SourceConfig`, gated by a `model_validator` that only requires the fields relevant to the chosen
`type`. To add a new source type: extend `SourceConfig` + its validator, write a `collect()`
function returning `CollectionResult`, and add a branch in `pipeline.collect_stage`.

**Cleaning** (`cleaning/cleaner.py`): `clean(df, config) -> (df, CleaningLog)` applies a *fixed
order*: dedupe → dtype coercion (lossless only — text is converted to numeric only if it
introduces zero new nulls) → missing values (per-column overrides first, then the global
strategy) → whitespace trimming → IQR-based outlier capping. Every action taken — or explicitly
*not* taken (e.g. "could not fill — column may be entirely empty") — is appended to a
`CleaningLog`, which flows straight into the report.

**Validation** (`validation/validator.py`): rule types (`not_null`, `unique`, `dtype`, `range`,
`allowed_values`, `regex`) are dispatched through a `dict[str, Checker]` table. Each checker
returns `Issue | None`; a checker that raises is caught and turned into an `Issue` rather than
crashing the whole `validate()` call. Add a new rule type by writing a checker and registering it
in `_CHECKERS`.

**Reporting** (`reporting/`): `eda.py` computes dataset/column stats, `charts.py` renders
matplotlib charts as base64-embedded PNGs (no external assets, so the HTML is self-contained),
`html_report.py` renders `templates/report.html.jinja` via Jinja2, and `pdf_report.py` renders the
*same* HTML through xhtml2pdf. xhtml2pdf was chosen over WeasyPrint specifically because it has
no system-level dependencies — it installs identically via pip on Windows/Mac/Linux — at the cost
of weaker CSS support (no flexbox), so the PDF layout is simpler than the HTML one.

**Two interfaces, one pipeline**: `cli/main.py` (Typer) wraps the stage functions for
step-by-step use (`dstk collect/clean/validate/report`, chaining Parquet/CSV intermediates via
`utils/io.py`) or full automation (`dstk run`). All commands are wrapped with a
`_friendly_errors` decorator that turns exceptions into a one-line `Error: ...` message + exit
code 1 instead of a raw traceback. `webapp/app.py` (Streamlit) wraps the exact same stage
functions in a 4-tab dashboard, using `st.session_state` to carry the in-progress DataFrame and
logs between tabs.

## Testing conventions

Tests mirror `src/dstoolkit/` module-for-module under `tests/`. `tests/conftest.py` has a shared
`messy_df` fixture (duplicates + nulls) for cleaning tests; `tests/data/sample.csv` is a fixture
with deliberate data-quality issues (dupes, nulls, an outlier, whitespace) used by collector and
end-to-end tests. The `db`/`api`/`web` collectors are unit-tested against mocks (`monkeypatch`),
not real network calls, to keep the suite fast and deterministic — real-network verification was
done ad hoc during development, not baked into the permanent suite.
