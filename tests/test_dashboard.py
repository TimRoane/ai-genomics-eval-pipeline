import pandas as pd

from genomics_eval.dashboard.app import (
    build_case_detail,
    compute_dashboard_metrics,
    detail_rows_table,
    failed_critical_cases,
    field_accuracy_counts_table,
    failure_mode_legend_table,
    has_assessable_content,
    hard_threshold_note,
    metric_tile_class,
    prepare_case_table,
    regression_checks_table,
    selected_row_index,
    summarize_failure_categories,
    summarize_tags,
    summarize_variant_type_accuracy,
    variant_type_accuracy_column_config,
)
from genomics_eval.scoring.failure_modes import FAILURE_MODES


def test_summarize_failure_categories_groups_modes():
    df = pd.DataFrame(
        [
            {
                "case_id": "case-1",
                "severity": "medium",
                "failure_modes": ["OVERCONFIDENT_VUS", "WRONG_CLASSIFICATION"],
            }
        ]
    )

    summary, details = summarize_failure_categories(df)

    assert summary.iloc[0]["category"] == "Clinical Interpretation"
    assert summary.iloc[0]["occurrences"] == 2
    assert set(details["failure_mode"]) == {"OVERCONFIDENT_VUS", "WRONG_CLASSIFICATION"}


def test_summarize_failure_categories_empty_run():
    df = pd.DataFrame([{"case_id": "case-1", "severity": "critical", "failure_modes": []}])
    summary, details = summarize_failure_categories(df)
    assert summary.empty
    assert details.empty


def test_failure_mode_legend_covers_all_modes():
    legend = failure_mode_legend_table()

    assert set(legend["failure_mode"]) == FAILURE_MODES
    assert legend["category"].notna().all()
    assert legend["explanation"].str.len().min() > 20


def test_compute_dashboard_metrics():
    df = pd.DataFrame(
        [
            {
                "case_id": "case-1",
                "passed": True,
                "severity": "critical",
                "classification_correct": True,
                "transcript_correct": True,
                "hallucination_detected": False,
                "failure_modes": [],
            },
            {
                "case_id": "case-2",
                "passed": False,
                "severity": "medium",
                "classification_correct": False,
                "transcript_correct": None,
                "hallucination_detected": True,
                "failure_modes": ["WRONG_CLASSIFICATION"],
            },
            {
                "case_id": "case-3",
                "passed": False,
                "severity": "medium",
                "classification_correct": False,
                "transcript_correct": False,
                "hallucination_detected": False,
                "failure_modes": ["NO_OUTPUT"],
            },
        ]
    )

    metrics = compute_dashboard_metrics(df, {"passed": False, "hard_threshold_checks": {"overall_pass_rate": True, "transcript_accuracy": False}})

    assert metrics["case_count"] == 3
    assert metrics["overall_pass_rate"] == 0.3333333333333333
    assert metrics["critical_case_pass_rate"] == 1.0
    assert metrics["classification_accuracy"] == 0.5
    assert metrics["transcript_accuracy"] == 1.0
    assert metrics["release_passed"] is False
    assert metrics["hard_threshold_passed"] is False


def test_summarize_tags_orders_lowest_pass_rate_first():
    df = pd.DataFrame(
        [
            {"case_id": "case-1", "passed": True, "tags": ["hgvs", "brca"]},
            {"case_id": "case-2", "passed": False, "tags": ["hgvs", "negative_control"]},
        ]
    )

    tag_df = summarize_tags(df)

    assert tag_df.iloc[0]["tag"] == "negative_control"
    assert "hgvs" in set(tag_df["tag"])


def test_summarize_variant_type_accuracy_excludes_output_quality_failures():
    df = pd.DataFrame(
        [
            {
                "case_id": "snv-pass",
                "tags": ["snv"],
                "failure_modes": [],
                "gene_correct": True,
                "classification_correct": True,
                "condition_correct": True,
                "transcript_correct": True,
            },
            {
                "case_id": "snv-wrong-class",
                "tags": ["snv"],
                "failure_modes": ["WRONG_CLASSIFICATION"],
                "gene_correct": True,
                "classification_correct": False,
                "condition_correct": True,
                "transcript_correct": None,
            },
            {
                "case_id": "deletion-no-output",
                "tags": ["deletion"],
                "failure_modes": ["NO_OUTPUT"],
                "gene_correct": False,
                "classification_correct": False,
                "condition_correct": False,
                "transcript_correct": False,
            },
        ]
    )

    summary = summarize_variant_type_accuracy(df)

    assert summary["variant_type"].tolist() == ["snv"]
    assert summary.iloc[0]["assessable_cases"] == 2
    assert summary.iloc[0]["classification_accuracy"] == 0.5
    assert summary.iloc[0]["transcript_accuracy"] == 1.0


def test_variant_type_accuracy_column_config_uses_compact_labels():
    config = variant_type_accuracy_column_config()

    assert config["variant_type"]["label"] == "type"
    assert config["assessable_cases"]["label"] == "cases"
    assert config["classification_accuracy"]["label"] == "classification"


def test_prepare_case_table_formats_lists():
    df = pd.DataFrame(
        [
            {
                "case_id": "case-1",
                "passed": False,
                "severity": "medium",
                "failure_modes": ["WRONG_GENE", "HGVS_MISMATCH"],
                "tags": ["hgvs", "negative_control"],
            }
        ]
    )

    table = prepare_case_table(df)

    assert table.iloc[0]["passed"] == "FAIL"
    assert table.iloc[0]["failure_count"] == 2
    assert table.iloc[0]["failure_modes"] == "WRONG_GENE, HGVS_MISMATCH"
    assert table.iloc[0]["tags"] == "hgvs, negative_control"


def test_failed_critical_cases_uses_display_status():
    table = pd.DataFrame(
        [
            {"case_id": "case-1", "passed": "FAIL", "severity": "critical"},
            {"case_id": "case-2", "passed": "PASS", "severity": "critical"},
            {"case_id": "case-3", "passed": "FAIL", "severity": "medium"},
        ]
    )

    critical = failed_critical_cases(table)

    assert critical["case_id"].tolist() == ["case-1"]


def test_regression_checks_table():
    table = regression_checks_table({"checks": {"overall_pass_rate": True, "max_overall_drop": False}})
    assert set(table["check"]) == {"overall pass rate", "max overall drop"}
    assert table["passed"].tolist().count(False) == 1


def test_regression_checks_table_splits_hard_and_baseline_checks():
    table = regression_checks_table(
        {
            "hard_threshold_checks": {"overall_pass_rate": True},
            "regression_checks": {"max_overall_drop": False},
        }
    )

    assert table["type"].tolist() == ["hard threshold", "baseline regression"]
    assert table["passed"].tolist() == [True, False]


def test_field_accuracy_counts_table():
    table = field_accuracy_counts_table(
        {
            "gene_accuracy": {"correct": 49, "incorrect": 1, "assessable": 50},
            "classification_accuracy": {"correct": 48, "incorrect": 2, "assessable": 50},
        }
    )

    assert table["metric"].tolist() == ["classification_accuracy", "gene_accuracy"]
    assert table["assessable"].tolist() == [50, 50]


def test_metric_tile_class_and_hard_threshold_note():
    checks = {"overall_pass_rate": True, "transcript_accuracy": False}

    assert metric_tile_class(checks, "overall_pass_rate") == "metric-tile-pass"
    assert metric_tile_class(checks, "transcript_accuracy") == "metric-tile-fail"
    assert metric_tile_class(checks, None) == "metric-tile-neutral"
    assert hard_threshold_note(checks, "transcript_accuracy") == "Hard threshold: FAIL"


def test_has_assessable_content_excludes_output_quality_failures():
    assert has_assessable_content(["WRONG_GENE"])
    assert not has_assessable_content(["NO_OUTPUT"])
    assert not has_assessable_content(["PARSER_FAILURE", "WRONG_GENE"])


def test_build_case_detail_merges_sources():
    scores = pd.DataFrame(
        [
            {
                "case_id": "case-1",
                "passed": False,
                "severity": "medium",
                "gene_correct": True,
                "transcript_correct": False,
                "hgvs_correct": True,
                "classification_correct": True,
                "condition_correct": True,
                "source_supported": None,
                "hallucination_detected": False,
                "failure_modes": ["WRONG_TRANSCRIPT"],
                "tags": ["hgvs"],
            }
        ]
    )
    detail_sources = {
        "cases": {
            "case-1": {
                "case_id": "case-1",
                "input_type": "HGVS",
                "input_variant": "NM_007294.4:c.68_69del",
                "assembly": "GRCh38",
                "question": "Interpret?",
                "expected_gene": "BRCA1",
                "expected_transcript": "NM_007294.4",
                "expected_hgvs_c": "NM_007294.4:c.68_69del",
                "expected_classification": "Pathogenic",
                "expected_condition": "Hereditary breast and ovarian cancer syndrome",
                "tags": ["hgvs", "negative_control"],
                "metadata": {"mock_failure_modes": ["wrong_transcript"]},
            }
        },
        "outputs": {
            "case-1": {
                "case_id": "case-1",
                "model_name": "mock",
                "prompt_version": "v1",
                "extracted_gene": "BRCA1",
                "extracted_transcript": "NM_000000.0",
                "extracted_hgvs": "NM_007294.4:c.68_69del",
                "extracted_classification": "Pathogenic",
                "extracted_condition": "Hereditary breast and ovarian cancer syndrome",
                "limitations": ["classification depends on source/version"],
                "cited_sources": [],
                "response_text": "{}",
            }
        },
        "annotations": {
            "case-1": {
                "case_id": "case-1",
                "normalized_key": None,
                "gene_symbol": "BRCA1",
                "dbsnp_id": "rs80357914",
                "clinvar_clnsig": "Pathogenic",
                "transcript_options": ["NM_007294.4"],
            }
        },
    }

    detail = build_case_detail("case-1", scores, detail_sources)

    assert detail["summary"]["failure_modes"] == "WRONG_TRANSCRIPT"
    assert detail["warnings"] == []
    assert {"field": "mock_failure_modes", "value": "wrong_transcript"} in detail["input"]
    assert detail["expected_vs_extracted"][1]["extracted"] == "NM_000000.0"
    assert {"field": "dbsnp_id", "value": "rs80357914"} in detail["annotation"]


def test_build_case_detail_handles_missing_optional_sources():
    scores = pd.DataFrame(
        [
            {
                "case_id": "case-1",
                "passed": False,
                "severity": "medium",
                "failure_modes": ["NO_OUTPUT"],
            }
        ]
    )

    detail = build_case_detail("case-1", scores, {"cases": {}, "outputs": {}, "annotations": {}})

    assert "Input case details are unavailable." in detail["warnings"]
    assert "AI output details are unavailable." in detail["warnings"]
    assert "Annotation details are unavailable." in detail["warnings"]
    assert detail["input"] == []
    assert detail["ai_output"] == []


def test_build_case_detail_formats_vcf_input_fields():
    scores = pd.DataFrame([{"case_id": "case-1", "passed": True, "severity": "medium", "failure_modes": []}])
    detail = build_case_detail(
        "case-1",
        scores,
        {
            "cases": {
                "case-1": {
                    "case_id": "case-1",
                    "input_type": "VCF_RECORD",
                    "assembly": "GRCh38",
                    "question": "Interpret?",
                    "chrom": "19",
                    "pos": 44908684,
                    "ref": "T",
                    "alt": "C",
                    "tags": ["vcf"],
                }
            },
            "outputs": {},
            "annotations": {},
        },
    )

    assert {"field": "chrom", "value": "19"} in detail["input"]
    assert {"field": "pos", "value": 44908684} in detail["input"]
    assert {"field": "ref", "value": "T"} in detail["input"]
    assert {"field": "alt", "value": "C"} in detail["input"]


def test_detail_rows_table_normalizes_mixed_display_values():
    table = detail_rows_table(
        [
            {"field": "gene_correct", "value": True},
            {"field": "source_supported", "value": None},
            {"field": "failure_modes", "value": "none"},
        ]
    )

    assert table["value"].tolist() == ["true", "none", "none"]
    assert all(isinstance(value, str) for value in table["value"])


def test_selected_row_index_supports_streamlit_selection_shape():
    assert selected_row_index({"selection": {"rows": [3]}}) == 3
    assert selected_row_index({"selection": {"rows": []}}) is None
