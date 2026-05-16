from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from genomics_eval.scoring.failure_modes import FAILURE_MODES
from genomics_eval.variant_types import variant_type_from_tags


FAILURE_MODE_CATEGORIES = {
    "Variant Identity": {
        "accent": "#2563eb",
        "description": "Gene, transcript, HGVS, and normalization mismatches.",
        "modes": {
            "WRONG_GENE",
            "WRONG_TRANSCRIPT",
            "HGVS_MISMATCH",
            "VARIANT_NORMALIZATION_ERROR",
        },
    },
    "Clinical Interpretation": {
        "accent": "#b45309",
        "description": "Classification, disease mapping, and overconfident interpretation errors.",
        "modes": {
            "WRONG_CLASSIFICATION",
            "DISEASE_MAPPING_ERROR",
            "OVERCONFIDENT_VUS",
            "MISREAD_CLINVAR_CONFLICT",
        },
    },
    "Evidence Support": {
        "accent": "#0f766e",
        "description": "Unsupported claims, hallucinated sources, and missing limitations.",
        "modes": {
            "HALLUCINATED_SOURCE",
            "UNSUPPORTED_MEDICAL_CLAIM",
            "MISSING_LIMITATION",
        },
    },
    "Output Quality": {
        "accent": "#7c3aed",
        "description": "Missing model output or parser failures.",
        "modes": {
            "NO_OUTPUT",
            "PARSER_FAILURE",
        },
    },
}


FAILURE_MODE_EXPLANATIONS = {
    "WRONG_GENE": "The answer names a different gene than the curated expected gene.",
    "WRONG_TRANSCRIPT": "A transcript-specific case expected a particular transcript, but the answer omitted it or used another transcript.",
    "HGVS_MISMATCH": "The reported HGVS expression does not match the curated expected HGVS representation.",
    "VARIANT_NORMALIZATION_ERROR": "The variant could not be normalized to the expected canonical representation.",
    "WRONG_CLASSIFICATION": "The clinical classification differs from the expected pathogenicity category.",
    "DISEASE_MAPPING_ERROR": "The answer maps the variant to the wrong disease, condition, or phenotype context.",
    "OVERCONFIDENT_VUS": "A benign, likely benign, or uncertain-significance variant was overcalled as pathogenic or likely pathogenic.",
    "MISREAD_CLINVAR_CONFLICT": "The answer ignores or misstates conflicting ClinVar evidence.",
    "HALLUCINATED_SOURCE": "The answer cites a source that was not present in the annotation context.",
    "UNSUPPORTED_MEDICAL_CLAIM": "The answer makes a medical claim not supported by the provided evidence.",
    "MISSING_LIMITATION": "The answer provides a clinical classification without noting source/version or evidence limitations.",
    "NO_OUTPUT": "The model returned no response for the case.",
    "PARSER_FAILURE": "The model response could not be parsed as the expected structured JSON.",
}


APP_CSS = """
<style>
html, body, [class*="css"] {
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.block-container {
  padding-top: 2rem;
  padding-bottom: 3rem;
  max-width: 1320px;
}
h1, h2, h3 {
  letter-spacing: 0;
}
.dashboard-header {
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 1rem;
  margin-bottom: 1.25rem;
}
.dashboard-title {
  color: #111827;
  font-size: 2rem;
  font-weight: 750;
  line-height: 1.1;
  margin: 0;
}
.dashboard-subtitle {
  color: #6b7280;
  font-size: 0.92rem;
  margin-top: 0.35rem;
}
.status-pill {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  padding: 0.35rem 0.65rem;
  text-transform: uppercase;
}
.status-pass {
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  color: #047857;
}
.status-fail {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
}
.metric-grid {
  display: grid;
  gap: 0.85rem;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  margin: 0.4rem 0 1.35rem;
}
.metric-tile {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 0.85rem 0.95rem;
  min-height: 90px;
}
.metric-tile-pass {
  border-top: 4px solid #059669;
}
.metric-tile-fail {
  border-top: 4px solid #dc2626;
}
.metric-tile-neutral {
  border-top: 4px solid #9ca3af;
}
.metric-label {
  color: #6b7280;
  font-size: 0.76rem;
  font-weight: 650;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}
.metric-value {
  color: #111827;
  font-size: 1.65rem;
  font-weight: 760;
  line-height: 1.2;
  margin-top: 0.35rem;
}
.metric-note {
  color: #6b7280;
  font-size: 0.78rem;
  margin-top: 0.25rem;
}
.category-grid {
  display: grid;
  gap: 0.85rem;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin: 0.3rem 0 1rem;
}
.category-tile {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-left: 5px solid var(--accent);
  border-radius: 8px;
  padding: 0.85rem 0.95rem;
}
.category-name {
  color: #111827;
  font-size: 0.95rem;
  font-weight: 750;
}
.category-count {
  color: #111827;
  font-size: 1.35rem;
  font-weight: 760;
  margin-top: 0.45rem;
}
.category-meta {
  color: #6b7280;
  font-size: 0.78rem;
  margin-top: 0.15rem;
}
.section-rule {
  border-top: 1px solid #e5e7eb;
  margin: 1.4rem 0 1rem;
}
div[data-testid="stDataFrame"] {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
}
div[data-testid="stDialog"] {
  width: min(94vw, 1280px) !important;
  max-width: min(94vw, 1280px) !important;
  margin-left: auto !important;
  margin-right: auto !important;
}
div[data-testid="stDialog"] > div {
  width: 100% !important;
  max-width: 100% !important;
}
.triage-help {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  color: #1e3a8a;
  font-size: 0.88rem;
  margin: 0.2rem 0 0.65rem;
  padding: 0.65rem 0.8rem;
}
@media (max-width: 1000px) {
  .metric-grid,
  .category-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 640px) {
  .metric-grid,
  .category-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
"""


def main(
    scores_path: str = "data/results/scores.parquet",
    regression_path: str = "data/results/regression_report.json",
    outputs_path: str = "data/results/ai_outputs.jsonl",
    cases_path: str = "data/raw/input_cases.jsonl",
    annotations_path: str = "data/processed/annotated_variants.parquet",
) -> None:
    st.set_page_config(page_title="Genomics Eval Dashboard", layout="wide")
    st.markdown(APP_CSS, unsafe_allow_html=True)

    scores_file = Path(scores_path)
    if not scores_file.exists():
        st.warning(f"No scores found at {scores_file}")
        return

    df = pd.read_parquet(scores_file)
    detail_sources = load_detail_sources(outputs_path, cases_path, annotations_path)
    report = load_regression_report(regression_path)
    metrics = compute_dashboard_metrics(df, report)

    render_header(metrics)
    render_metric_tiles(metrics)

    st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)
    st.subheader("Failure Categories")
    category_summary, category_details = summarize_failure_categories(df)
    render_failure_categories(category_summary)
    render_failure_details(category_summary, category_details)
    render_failure_mode_legend()

    st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)
    left, right = st.columns([1.05, 1.35], gap="large")
    with left:
        st.subheader("Regression Gate")
        render_regression_panel(report)
    with right:
        st.subheader("Accuracy By Tag")
        tag_df = summarize_tags(df)
        if tag_df.empty:
            st.info("No tags available.")
        else:
            st.dataframe(
                tag_df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "pass_rate": st.column_config.ProgressColumn("pass_rate", format="%.1f", min_value=0, max_value=1),
                },
            )
        st.subheader("Accuracy By Variant Type")
        variant_type_df = summarize_variant_type_accuracy(df)
        if variant_type_df.empty:
            st.info("No variant-type tags available.")
        else:
            st.dataframe(
                variant_type_df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "gene_accuracy": st.column_config.ProgressColumn("gene_accuracy", format="%.1f", min_value=0, max_value=1),
                    "classification_accuracy": st.column_config.ProgressColumn("classification_accuracy", format="%.1f", min_value=0, max_value=1),
                    "condition_accuracy": st.column_config.ProgressColumn("condition_accuracy", format="%.1f", min_value=0, max_value=1),
                    "transcript_accuracy": st.column_config.ProgressColumn("transcript_accuracy", format="%.1f", min_value=0, max_value=1),
                },
            )

    st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)
    st.subheader("Case Triage")
    triage_df = prepare_case_table(df)
    st.markdown(
        '<div class="triage-help">Select any case row, especially the <strong>case_id</strong>, to open the detailed review modal.</div>',
        unsafe_allow_html=True,
    )
    selection = st.dataframe(
        triage_df,
        hide_index=True,
        use_container_width=True,
        column_order=["case_id", "passed", "severity", "failure_count", "failure_modes", "tags"],
        column_config={
            "passed": st.column_config.TextColumn("status"),
            "case_id": st.column_config.TextColumn("case_id", help="Select this row to open the case detail modal."),
        },
        on_select="rerun",
        selection_mode="single-row",
        key="case-triage-table",
    )
    selected_index = selected_row_index(selection)
    if selected_index is not None and selected_index < len(triage_df):
        case_id = str(triage_df.iloc[selected_index]["case_id"])
        detail = build_case_detail(case_id, df, detail_sources)
        render_case_detail_dialog(detail)

    critical_df = failed_critical_cases(triage_df)
    if not critical_df.empty:
        st.subheader("Failed Critical Cases")
        st.dataframe(critical_df, hide_index=True, use_container_width=True)


def render_header(metrics: dict[str, Any]) -> None:
    status_class = "status-pass" if metrics["release_passed"] else "status-fail"
    status_text = "Release Gate Pass" if metrics["release_passed"] else "Release Gate Fail"
    hard_status_class = "status-pass" if metrics["hard_threshold_passed"] else "status-fail"
    hard_status_text = "Hard Thresholds Pass" if metrics["hard_threshold_passed"] else "Hard Thresholds Fail"
    st.markdown(
        f"""
        <div class="dashboard-header">
          <div style="display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;flex-wrap:wrap;">
            <div>
              <h1 class="dashboard-title">AI Genomics Evaluation</h1>
              <div class="dashboard-subtitle">{metrics["case_count"]} cases evaluated across HGVS normalization, annotation, scoring, and regression checks.</div>
            </div>
            <div style="display:flex;gap:0.5rem;flex-wrap:wrap;justify-content:flex-end;">
              <span class="status-pill {hard_status_class}">{hard_status_text}</span>
              <span class="status-pill {status_class}">{status_text}</span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_tiles(metrics: dict[str, Any]) -> None:
    tiles = [
        ("Overall Pass Rate", format_rate(metrics["overall_pass_rate"]), f'{metrics["passed_cases"]}/{metrics["case_count"]} cases passed', "overall_pass_rate"),
        ("Critical Pass Rate", format_rate(metrics["critical_case_pass_rate"]), f'{metrics["critical_failures"]} critical failures', "critical_case_pass_rate"),
        ("Classification", format_rate(metrics["classification_accuracy"]), "classification accuracy", None),
        ("Transcript", format_rate(metrics["transcript_accuracy"]), "required transcript accuracy", "transcript_accuracy"),
        ("Hallucination", format_rate(metrics["hallucination_rate"]), "source hallucination rate", "hallucination_rate_max"),
    ]
    html = ['<div class="metric-grid">']
    for label, value, note, check_key in tiles:
        tile_class = metric_tile_class(metrics["hard_threshold_checks"], check_key)
        threshold_note = hard_threshold_note(metrics["hard_threshold_checks"], check_key)
        html.append(
            (
                f'<div class="metric-tile {tile_class}">'
                f'<div class="metric-label">{label}</div>'
                f'<div class="metric-value">{value}</div>'
                f'<div class="metric-note">{note}</div>'
                f'<div class="metric-note">{threshold_note}</div>'
                "</div>"
            )
        )
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)


def render_failure_categories(category_summary: pd.DataFrame) -> None:
    if category_summary.empty:
        st.success("No failures detected in this run.")
        return
    html = ['<div class="category-grid">']
    for row in category_summary.to_dict("records"):
        config = FAILURE_MODE_CATEGORIES.get(row["category"], {"accent": "#4b5563"})
        html.append(
            (
                f'<div class="category-tile" style="--accent:{config["accent"]};">'
                f'<div class="category-name">{row["category"]}</div>'
                f'<div class="category-count">{row["occurrences"]}</div>'
                f'<div class="category-meta">{row["affected_cases"]} affected cases</div>'
                f'<div class="category-meta">Highest severity: {row["highest_severity"]}</div>'
                "</div>"
            )
        )
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)


def render_failure_details(category_summary: pd.DataFrame, category_details: pd.DataFrame) -> None:
    if category_summary.empty:
        return
    tabs = st.tabs(category_summary["category"].tolist())
    for tab, category in zip(tabs, category_summary["category"].tolist()):
        with tab:
            rows = category_details[category_details["category"] == category]
            st.dataframe(
                rows[["failure_mode", "occurrences", "affected_cases", "highest_severity"]],
                hide_index=True,
                use_container_width=True,
            )


def render_failure_mode_legend() -> None:
    legend_df = failure_mode_legend_table()
    with st.expander("Failure Mode Legend", expanded=False):
        st.caption("Reference for every controlled failure mode used by the scorer. Categories are textual so the legend does not rely on color alone.")
        st.dataframe(
            legend_df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "failure_mode": st.column_config.TextColumn("failure_mode"),
                "category": st.column_config.TextColumn("category"),
                "explanation": st.column_config.TextColumn("explanation", width="large"),
            },
        )


def render_regression_panel(report: dict[str, Any] | None) -> None:
    if not report:
        st.info("No regression report found.")
        return
    checks_df = regression_checks_table(report)
    if checks_df.empty:
        st.info("No regression checks available.")
    else:
        st.dataframe(
            checks_df,
            hide_index=True,
            use_container_width=True,
            column_config={"passed": st.column_config.CheckboxColumn("passed")},
        )
    with st.expander("Regression Metrics", expanded=False):
        current = report.get("current_metrics", {})
        baseline = report.get("baseline_metrics", {}) or {}
        metrics = sorted(set(current) & set(baseline))
        rows = [
            {
                "metric": metric,
                "current": current.get(metric),
                "baseline": baseline.get(metric),
            }
            for metric in metrics
            if isinstance(current.get(metric), int | float) and isinstance(baseline.get(metric), int | float)
        ]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        field_counts = field_accuracy_counts_table(current.get("field_accuracy_counts", {}))
        if not field_counts.empty:
            st.caption("Field accuracy counts exclude output-quality failures such as NO_OUTPUT and PARSER_FAILURE.")
            st.dataframe(field_counts, hide_index=True, use_container_width=True)


@st.dialog("Case Detail", width="large")
def render_case_detail_dialog(detail: dict[str, Any]) -> None:
    status_class = "status-pass" if detail["summary"].get("passed") else "status-fail"
    status_text = "Pass" if detail["summary"].get("passed") else "Fail"
    st.markdown(
        (
            '<div style="display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;flex-wrap:wrap;">'
            f'<div><h3 style="margin:0;">{detail["case_id"]}</h3>'
            f'<div style="color:#6b7280;font-size:0.85rem;">Severity: {detail["summary"].get("severity", "unknown")} · '
            f'{detail["summary"].get("failure_count", 0)} failure modes</div></div>'
            f'<span class="status-pill {status_class}">{status_text}</span>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    for warning in detail["warnings"]:
        st.warning(warning)

    st.markdown("#### Input")
    st.dataframe(detail_rows_table(detail["input"]), hide_index=True, use_container_width=True)

    st.markdown("#### Expected vs Extracted")
    st.dataframe(detail_rows_table(detail["expected_vs_extracted"]), hide_index=True, use_container_width=True)

    st.markdown("#### Scoring")
    st.dataframe(detail_rows_table(detail["scoring"]), hide_index=True, use_container_width=True)

    st.markdown("#### Annotation Context")
    if detail["annotation"]:
        st.dataframe(detail_rows_table(detail["annotation"]), hide_index=True, use_container_width=True)
    else:
        st.info("No annotation detail available for this case.")

    st.markdown("#### AI Output")
    if detail["ai_output"]:
        st.dataframe(detail_rows_table(detail["ai_output"]), hide_index=True, use_container_width=True)
        response_text = detail.get("raw_response_text")
        if response_text:
            with st.expander("Raw response_text", expanded=False):
                st.code(response_text, language="json")
    else:
        st.info("No AI output detail available for this case.")


def compute_dashboard_metrics(df: pd.DataFrame, report: dict[str, Any] | None = None) -> dict[str, Any]:
    total = len(df)
    critical_df = df[df["severity"] == "critical"] if "severity" in df.columns else pd.DataFrame()
    content_df = df[df["failure_modes"].apply(has_assessable_content)] if "failure_modes" in df.columns else df
    transcript_series = content_df["transcript_correct"].dropna() if "transcript_correct" in content_df.columns else pd.Series(dtype=bool)
    release_passed = bool(report.get("passed")) if report else True
    hard_threshold_checks = report.get("hard_threshold_checks", {}) if report else {}
    hard_threshold_passed = all(hard_threshold_checks.values()) if hard_threshold_checks else release_passed
    passed_cases = int(df["passed"].sum()) if "passed" in df.columns and total else 0
    return {
        "case_count": total,
        "passed_cases": passed_cases,
        "overall_pass_rate": float(df["passed"].mean()) if total else 0.0,
        "critical_case_pass_rate": float(critical_df["passed"].mean()) if len(critical_df) else 1.0,
        "classification_accuracy": float(content_df["classification_correct"].mean()) if len(content_df) else 1.0,
        "transcript_accuracy": float(transcript_series.mean()) if len(transcript_series) else 1.0,
        "hallucination_rate": float(df["hallucination_detected"].mean()) if total else 0.0,
        "critical_failures": int((~critical_df["passed"]).sum()) if len(critical_df) else 0,
        "release_passed": release_passed,
        "hard_threshold_checks": hard_threshold_checks,
        "hard_threshold_passed": hard_threshold_passed,
    }


def summarize_failure_categories(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if "failure_modes" not in df.columns:
        return pd.DataFrame(), pd.DataFrame()

    rows: list[dict] = []
    for row in df[["case_id", "severity", "failure_modes"]].to_dict("records"):
        for mode in _normalize_failure_modes(row.get("failure_modes")):
            rows.append(
                {
                    "case_id": row["case_id"],
                    "severity": row.get("severity"),
                    "failure_mode": mode,
                    "category": _failure_category(mode),
                }
            )
    if not rows:
        return pd.DataFrame(), pd.DataFrame()

    detail_df = pd.DataFrame(rows)
    detail_rows = []
    for (category, mode), group in detail_df.groupby(["category", "failure_mode"], sort=True):
        detail_rows.append(
            {
                "category": category,
                "failure_mode": mode,
                "occurrences": len(group),
                "affected_cases": ", ".join(sorted(group["case_id"].unique())),
                "highest_severity": _highest_severity(group["severity"].tolist()),
            }
        )
    category_rows = []
    for category, group in detail_df.groupby("category", sort=True):
        category_rows.append(
            {
                "category": category,
                "occurrences": len(group),
                "affected_cases": group["case_id"].nunique(),
                "highest_severity": _highest_severity(group["severity"].tolist()),
                "failure_modes": ", ".join(sorted(group["failure_mode"].unique())),
            }
        )
    return pd.DataFrame(category_rows), pd.DataFrame(detail_rows)


def failure_mode_legend_table() -> pd.DataFrame:
    rows = [
        {
            "failure_mode": mode,
            "category": _failure_category(mode),
            "explanation": FAILURE_MODE_EXPLANATIONS[mode],
        }
        for mode in sorted(FAILURE_MODES, key=lambda value: (_failure_category(value), value))
    ]
    return pd.DataFrame(rows)


def summarize_tags(df: pd.DataFrame) -> pd.DataFrame:
    if "tags" not in df.columns:
        return pd.DataFrame()
    rows: list[dict] = []
    for row in df[["case_id", "passed", "tags"]].to_dict("records"):
        for tag in _normalize_list(row.get("tags")):
            rows.append({"tag": tag, "case_id": row["case_id"], "passed": bool(row["passed"])})
    if not rows:
        return pd.DataFrame()
    tag_df = pd.DataFrame(rows)
    summary = (
        tag_df.groupby("tag", sort=True)
        .agg(cases=("case_id", "nunique"), passed=("passed", "sum"), pass_rate=("passed", "mean"))
        .reset_index()
        .sort_values(["pass_rate", "cases", "tag"], ascending=[True, False, True])
    )
    return summary


def summarize_variant_type_accuracy(df: pd.DataFrame) -> pd.DataFrame:
    if "tags" not in df.columns or "failure_modes" not in df.columns:
        return pd.DataFrame()
    content_df = df[df["failure_modes"].apply(has_assessable_content)].copy()
    if content_df.empty:
        return pd.DataFrame()
    if "variant_type" not in content_df.columns:
        content_df["variant_type"] = content_df["tags"].apply(lambda tags: variant_type_from_tags(_normalize_list(tags)))
    else:
        content_df["variant_type"] = content_df.apply(
            lambda row: row["variant_type"]
            if row.get("variant_type") and row["variant_type"] != "unclassified"
            else variant_type_from_tags(_normalize_list(row.get("tags"))),
            axis=1,
        )
    rows: list[dict[str, Any]] = []
    for variant_type, group in content_df.groupby("variant_type", sort=True):
        transcript_series = group["transcript_correct"].dropna() if "transcript_correct" in group.columns else pd.Series(dtype=bool)
        rows.append(
            {
                "variant_type": variant_type,
                "assessable_cases": len(group),
                "gene_accuracy": float(group["gene_correct"].mean()) if "gene_correct" in group.columns else 1.0,
                "classification_accuracy": float(group["classification_correct"].mean()) if "classification_correct" in group.columns else 1.0,
                "condition_accuracy": float(group["condition_correct"].mean()) if "condition_correct" in group.columns else 1.0,
                "transcript_accuracy": float(transcript_series.mean()) if len(transcript_series) else 1.0,
            }
        )
    return pd.DataFrame(rows)


def prepare_case_table(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for row in df.to_dict("records"):
        modes = _normalize_failure_modes(row.get("failure_modes"))
        rows.append(
            {
                "case_id": row.get("case_id"),
                "passed": "PASS" if bool(row.get("passed")) else "FAIL",
                "severity": row.get("severity"),
                "failure_count": len(modes),
                "failure_modes": ", ".join(modes),
                "tags": ", ".join(_normalize_list(row.get("tags"))),
            }
        )
    return pd.DataFrame(rows).sort_values(["passed", "severity", "case_id"], ascending=[True, True, True])


def failed_critical_cases(triage_df: pd.DataFrame) -> pd.DataFrame:
    if triage_df.empty:
        return triage_df
    return triage_df[(triage_df["severity"] == "critical") & (triage_df["passed"] == "FAIL")]


def build_case_detail(case_id: str, scores_df: pd.DataFrame, detail_sources: dict[str, dict[str, dict]]) -> dict[str, Any]:
    score = first_record_by_case_id(scores_df, case_id)
    case = detail_sources.get("cases", {}).get(case_id)
    output = detail_sources.get("outputs", {}).get(case_id)
    annotation = detail_sources.get("annotations", {}).get(case_id)
    warnings = []
    if case is None:
        warnings.append("Input case details are unavailable.")
    if output is None:
        warnings.append("AI output details are unavailable.")
    if annotation is None:
        warnings.append("Annotation details are unavailable.")

    failure_modes = _normalize_failure_modes(score.get("failure_modes"))
    summary = {
        "passed": bool(score.get("passed")),
        "severity": score.get("severity", case.get("severity") if case else "unknown"),
        "failure_count": len(failure_modes),
        "failure_modes": ", ".join(failure_modes) or "none",
    }
    return {
        "case_id": case_id,
        "summary": summary,
        "warnings": warnings,
        "input": case_input_rows(case),
        "expected_vs_extracted": expected_vs_extracted_rows(case, output),
        "scoring": scoring_rows(score),
        "annotation": annotation_rows(annotation),
        "ai_output": ai_output_rows(output),
        "raw_response_text": output.get("response_text") if output else None,
    }


def case_input_rows(case: dict | None) -> list[dict[str, Any]]:
    if not case:
        return []
    rows = [
        {"field": "input_type", "value": case.get("input_type")},
        {"field": "assembly", "value": case.get("assembly")},
        {"field": "question", "value": case.get("question")},
        {"field": "tags", "value": ", ".join(_normalize_list(case.get("tags")))},
    ]
    if case.get("input_type") == "HGVS":
        rows.append({"field": "input_variant", "value": case.get("input_variant")})
    else:
        rows.extend(
            [
                {"field": "chrom", "value": case.get("chrom")},
                {"field": "pos", "value": case.get("pos")},
                {"field": "ref", "value": case.get("ref")},
                {"field": "alt", "value": case.get("alt")},
            ]
        )
    metadata = case.get("metadata") or {}
    if metadata:
        rows.append({"field": "mock_failure_modes", "value": ", ".join(_normalize_list(metadata.get("mock_failure_modes")))})
    return rows


def expected_vs_extracted_rows(case: dict | None, output: dict | None) -> list[dict[str, Any]]:
    fields = [
        ("gene", "expected_gene", "extracted_gene"),
        ("transcript", "expected_transcript", "extracted_transcript"),
        ("hgvs", "expected_hgvs_c", "extracted_hgvs"),
        ("classification", "expected_classification", "extracted_classification"),
        ("condition", "expected_condition", "extracted_condition"),
    ]
    return [
        {
            "field": label,
            "expected": case.get(expected_key) if case else None,
            "extracted": output.get(output_key) if output else None,
        }
        for label, expected_key, output_key in fields
    ]


def scoring_rows(score: dict) -> list[dict[str, Any]]:
    fields = [
        "gene_correct",
        "transcript_correct",
        "hgvs_correct",
        "classification_correct",
        "condition_correct",
        "source_supported",
        "hallucination_detected",
        "failure_modes",
    ]
    rows = []
    for field in fields:
        value = score.get(field)
        if field == "failure_modes":
            value = ", ".join(_normalize_failure_modes(value)) or "none"
        rows.append({"field": field, "value": value})
    return rows


def annotation_rows(annotation: dict | None) -> list[dict[str, Any]]:
    if not annotation:
        return []
    fields = [
        "normalized_key",
        "gene_symbol",
        "dbsnp_id",
        "clinvar_variation_id",
        "clinvar_clnsig",
        "clinvar_review_status",
        "clinvar_condition",
        "hgvs_c",
        "hgvs_p",
        "transcript_options",
        "annotation_warnings",
    ]
    return [{"field": field, "value": format_detail_value(annotation.get(field))} for field in fields]


def ai_output_rows(output: dict | None) -> list[dict[str, Any]]:
    if not output:
        return []
    fields = [
        "model_name",
        "prompt_version",
        "extracted_gene",
        "extracted_transcript",
        "extracted_hgvs",
        "extracted_classification",
        "extracted_condition",
        "cited_sources",
        "limitations",
        "explanation",
        "parser_failure",
    ]
    return [{"field": field, "value": format_detail_value(output.get(field))} for field in fields]


def detail_rows_table(rows: list[dict[str, Any]]) -> pd.DataFrame:
    table = pd.DataFrame(rows)
    for column in table.columns:
        table[column] = table[column].map(format_detail_display_value)
    return table


def regression_checks_table(report: dict[str, Any]) -> pd.DataFrame:
    rows = []
    hard_checks = report.get("hard_threshold_checks", {})
    regression_checks = report.get("regression_checks", {})
    if hard_checks or regression_checks:
        rows.extend(
            {
                "type": "hard threshold",
                "check": check.replace("_", " "),
                "passed": bool(passed),
            }
            for check, passed in sorted(hard_checks.items())
        )
        rows.extend(
            {
                "type": "baseline regression",
                "check": check.replace("_", " "),
                "passed": bool(passed),
            }
            for check, passed in sorted(regression_checks.items())
        )
    else:
        checks = report.get("checks", {})
        rows = [
            {
                "type": "gate check",
                "check": check.replace("_", " "),
                "passed": bool(passed),
            }
            for check, passed in sorted(checks.items())
        ]
    return pd.DataFrame(rows)


def field_accuracy_counts_table(field_counts: dict[str, dict[str, int]]) -> pd.DataFrame:
    rows = [
        {
            "metric": metric,
            "correct": counts.get("correct", 0),
            "incorrect": counts.get("incorrect", 0),
            "assessable": counts.get("assessable", 0),
        }
        for metric, counts in sorted(field_counts.items())
    ]
    return pd.DataFrame(rows)


def load_detail_sources(outputs_path: str | Path, cases_path: str | Path, annotations_path: str | Path) -> dict[str, dict[str, dict]]:
    return {
        "outputs": load_jsonl_by_case_id(outputs_path),
        "cases": load_jsonl_by_case_id(cases_path),
        "annotations": load_parquet_by_case_id(annotations_path),
    }


def load_jsonl_by_case_id(path: str | Path) -> dict[str, dict]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    rows: dict[str, dict] = {}
    with file_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            case_id = row.get("case_id")
            if case_id:
                rows[case_id] = normalize_detail_record(row)
    return rows


def load_parquet_by_case_id(path: str | Path) -> dict[str, dict]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    df = pd.read_parquet(file_path)
    rows = {}
    for row in df.to_dict("records"):
        record = normalize_detail_record(row)
        case_id = record.get("case_id")
        if case_id:
            rows[case_id] = record
    return rows


def load_regression_report(regression_path: str | Path) -> dict[str, Any] | None:
    regression_file = Path(regression_path)
    if not regression_file.exists():
        return None
    return json.loads(regression_file.read_text(encoding="utf-8"))


def selected_row_index(selection: Any) -> int | None:
    selected = getattr(selection, "selection", None)
    if selected is None and isinstance(selection, dict):
        selected = selection.get("selection")
    rows = getattr(selected, "rows", None)
    if rows is None and isinstance(selected, dict):
        rows = selected.get("rows")
    if not rows:
        return None
    return int(rows[0])


def first_record_by_case_id(df: pd.DataFrame, case_id: str) -> dict:
    matches = df[df["case_id"] == case_id]
    if matches.empty:
        return {"case_id": case_id, "passed": False, "failure_modes": []}
    return normalize_detail_record(matches.iloc[0].to_dict())


def normalize_detail_record(record: dict) -> dict:
    return {key: normalize_detail_value(value) for key, value in record.items()}


def normalize_detail_value(value):
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, list | tuple | dict):
        return value
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def format_detail_value(value) -> Any:
    value = normalize_detail_value(value)
    if isinstance(value, list):
        return ", ".join(str(item) for item in value if item) or None
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    return value


def format_detail_display_value(value) -> str:
    value = format_detail_value(value)
    if value is None:
        return "none"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def format_rate(value: float | int | None) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.1%}"


def metric_tile_class(hard_threshold_checks: dict[str, bool], check_key: str | None) -> str:
    if not check_key or check_key not in hard_threshold_checks:
        return "metric-tile-neutral"
    return "metric-tile-pass" if hard_threshold_checks[check_key] else "metric-tile-fail"


def hard_threshold_note(hard_threshold_checks: dict[str, bool], check_key: str | None) -> str:
    if not check_key or check_key not in hard_threshold_checks:
        return "No hard threshold"
    return "Hard threshold: PASS" if hard_threshold_checks[check_key] else "Hard threshold: FAIL"


def _normalize_failure_modes(value) -> list[str]:
    return _normalize_list(value)


def has_assessable_content(failure_modes) -> bool:
    return not (set(_normalize_failure_modes(failure_modes)) & {"NO_OUTPUT", "PARSER_FAILURE"})


def _normalize_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    try:
        return [str(item) for item in value if item]
    except TypeError:
        return []


def _failure_category(mode: str) -> str:
    for category, config in FAILURE_MODE_CATEGORIES.items():
        if mode in config["modes"]:
            return category
    return "Other"


def _highest_severity(values: list[str | None]) -> str:
    order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    present = [value for value in values if value]
    if not present:
        return "unknown"
    return max(present, key=lambda value: order.get(str(value).lower(), 0))


if __name__ == "__main__":
    main(*(sys.argv[1:6]))
