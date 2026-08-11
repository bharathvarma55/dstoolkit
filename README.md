# dstoolkit

A single command-line tool covering the standard data science workflow: **collect → clean →
validate → report**.

## Install

```bash
python -m venv .venv
.venv\Scripts\activate   # on Windows; use `source .venv/bin/activate` on Mac/Linux
pip install -e ".[dev]"
```

## Quick start

Run the full pipeline from a config file:

```bash
dstk run examples/pipeline.yaml
```

This reads `examples/sample_data.csv`, cleans it, validates it, and writes an HTML report.

## Step by step

Each stage can also be run independently, chaining intermediate files:

```bash
dstk collect examples/pipeline.yaml -o raw.parquet
dstk clean raw.parquet examples/pipeline.yaml -o clean.parquet
dstk validate clean.parquet examples/pipeline.yaml -o validation.json
dstk report clean.parquet examples/pipeline.yaml --validation validation.json -o report.html
```

`report -o` writes a PDF instead of HTML if the output path ends in `.pdf`.

## Web app

```bash
dstk serve
```

Opens a browser dashboard at `http://127.0.0.1:8000` — a dark, custom-built UI (FastAPI backend +
plain HTML/CSS/JS, no framework) that walks through upload → clean → validate → report, with an
inline report preview and HTML/PDF downloads. Runs single-user/local only: session state lives in
memory in the server process, so don't run it with multiple uvicorn workers.

## Streamlit dashboard (lightweight alternative)

```bash
streamlit run src/dstoolkit/webapp/app.py
```

A simpler four-tab dashboard built on Streamlit's default widgets, wired to the exact same
collect/clean/validate/report functions. Less polished than `dstk serve`, but zero frontend code
to maintain.

## Scope

- **Collect**:
  - local files — CSV, Excel, JSON, Parquet (`source.type: file`)
  - databases — any SQLAlchemy-supported connection string + SQL query (`source.type: db`)
  - REST APIs — JSON responses, with an optional dotted `json_path` into nested payloads
    (`source.type: api`)
  - web pages — a `<table>` element via `table_index`, or repeating elements via a CSS
    `selector` + per-field sub-selectors (`source.type: web`)
- **Clean**: deduplication, dtype coercion, missing-value handling, string normalization, outlier
  capping — with a human-readable log of every action taken
- **Validate**: declarative rules — `not_null`, `unique`, `dtype`, `range`, `allowed_values`, `regex`
- **Report**: a self-contained HTML file (dataset overview, cleaning log, validation results,
  column profiles, charts) and/or a PDF rendered from the same content via xhtml2pdf — pure
  Python, no system dependencies, so it installs the same way on Windows/Mac/Linux. The PDF has
  simpler layout than the HTML (xhtml2pdf doesn't support flexbox), but the same information.
  Charts are picked explicitly — `histogram`, `bar`, `box`, `scatter`, `line`, `pie`,
  `correlation`, `missingness` — in the web app's chart builder, or via `report.charts` in the
  YAML config; omit `report.charts` entirely to get the old automatic set (missingness +
  histograms + correlation) back.
- **Interfaces**: CLI (`dstk`), a custom FastAPI + HTML/CSS/JS web app (`dstk serve`), and a
  Streamlit dashboard — all built on the same collect/clean/validate/report functions.

See `examples/pipeline.yaml` for the full set of source-config fields per source type.
