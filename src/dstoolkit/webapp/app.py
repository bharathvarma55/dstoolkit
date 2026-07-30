"""Streamlit UI wrapping the same collect/clean/validate/report functions the CLI uses, so
there is one implementation of each stage. Run with:

    streamlit run src/dstoolkit/webapp/app.py
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from dstoolkit.cleaning.cleaner import clean
from dstoolkit.cleaning.rules import CleaningLog
from dstoolkit.collectors import file_collector
from dstoolkit.config import CleaningConfig, ValidationRuleConfig
from dstoolkit.reporting import html_report, pdf_report
from dstoolkit.validation.rules import ValidationResult
from dstoolkit.validation.validator import validate

st.set_page_config(page_title="dstoolkit", layout="wide")
st.title("dstoolkit — Data Science Toolkit")

for key, default in {
    "df": None,
    "cleaning_log": None,
    "validation_result": None,
    "rules": [],
    "report_html": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

tab_load, tab_clean, tab_validate, tab_report = st.tabs(
    ["1. Load Data", "2. Clean", "3. Validate", "4. Report"]
)

with tab_load:
    st.header("Load Data")
    uploaded = st.file_uploader(
        "Upload a CSV, Excel, JSON, or Parquet file",
        type=["csv", "xlsx", "xls", "json", "parquet"],
    )
    if uploaded is not None:
        tmp_path = Path(tempfile.gettempdir()) / uploaded.name
        tmp_path.write_bytes(uploaded.getvalue())
        result = file_collector.collect(tmp_path)
        st.session_state.df = result.df
        st.session_state.cleaning_log = None
        st.session_state.validation_result = None
        st.session_state.report_html = None
        st.success(f"Loaded {result.row_count} rows, {result.col_count} columns")

    if st.session_state.df is not None:
        st.dataframe(st.session_state.df.head(50))

with tab_clean:
    st.header("Clean")
    if st.session_state.df is None:
        st.info("Load data first.")
    else:
        dedupe = st.checkbox("Remove duplicate rows", value=True)
        missing_strategy = st.selectbox(
            "Missing value strategy", ["drop", "mean", "median", "mode", "constant"]
        )
        string_normalize = st.checkbox("Trim whitespace in text columns", value=True)
        outlier_strategy = st.selectbox("Outlier handling", ["iqr_cap", "none"])

        if st.button("Run cleaning"):
            config = CleaningConfig(
                dedupe=dedupe,
                missing_value_strategy=missing_strategy,
                string_normalize=string_normalize,
                outlier_strategy=outlier_strategy,
            )
            cleaned, log = clean(st.session_state.df, config)
            st.session_state.df = cleaned
            st.session_state.cleaning_log = log
            st.success("Cleaning complete")

        if st.session_state.cleaning_log and st.session_state.cleaning_log.actions:
            st.write("**Actions taken:**")
            for action in st.session_state.cleaning_log.as_text():
                st.write(f"- {action}")

        st.dataframe(st.session_state.df.head(50))

with tab_validate:
    st.header("Validate")
    if st.session_state.df is None:
        st.info("Load data first.")
    else:
        st.subheader("Add a rule")
        rule_type = st.selectbox(
            "Rule type", ["not_null", "unique", "dtype", "range", "allowed_values", "regex"]
        )
        column = st.selectbox("Column", list(st.session_state.df.columns))
        params: dict = {}
        if rule_type == "not_null":
            params["max_null_rate"] = st.slider("Max null rate", 0.0, 1.0, 0.0)
        elif rule_type == "dtype":
            params["expected"] = st.selectbox("Expected type", ["numeric", "string", "datetime", "bool"])
        elif rule_type == "range":
            params["min"] = st.number_input("Min", value=0.0)
            params["max"] = st.number_input("Max", value=100.0)
        elif rule_type == "allowed_values":
            values_str = st.text_input("Allowed values (comma-separated)")
            params["values"] = [v.strip() for v in values_str.split(",") if v.strip()]
        elif rule_type == "regex":
            params["pattern"] = st.text_input("Regex pattern")

        if st.button("Add rule"):
            st.session_state.rules.append(
                ValidationRuleConfig(type=rule_type, column=column, params=params)
            )

        if st.session_state.rules:
            st.write("**Rules:**")
            for i, rule in enumerate(st.session_state.rules):
                col1, col2 = st.columns([5, 1])
                col1.write(f"{i + 1}. `{rule.type}` on **{rule.column}** {rule.params}")
                if col2.button("Remove", key=f"remove_rule_{i}"):
                    st.session_state.rules.pop(i)
                    st.rerun()

        if st.button("Run validation"):
            st.session_state.validation_result = validate(st.session_state.df, st.session_state.rules)

        if st.session_state.validation_result is not None:
            result = st.session_state.validation_result
            if result.passed:
                st.success(f"All {result.rules_evaluated} rule(s) passed")
            else:
                st.error(f"{len(result.issues)} issue(s) found")
                for issue in result.issues:
                    st.write(f"- `[{issue.rule}]` **{issue.column}**: {issue.message}")

with tab_report:
    st.header("Report")
    if st.session_state.df is None:
        st.info("Load data first.")
    else:
        title = st.text_input("Report title", value="Data Science Report")
        if st.button("Generate report"):
            log = st.session_state.cleaning_log or CleaningLog()
            result = st.session_state.validation_result or ValidationResult()
            st.session_state.report_html = html_report.render(
                st.session_state.df, log, result, title=title
            )

        if st.session_state.report_html:
            st.components.v1.html(st.session_state.report_html, height=800, scrolling=True)
            st.download_button(
                "Download HTML", st.session_state.report_html, file_name="report.html", mime="text/html"
            )
            st.download_button(
                "Download PDF",
                pdf_report.render_bytes(st.session_state.report_html),
                file_name="report.pdf",
                mime="application/pdf",
            )
