from genomics_eval.regression.compare_runs import compare_to_baseline
from genomics_eval.regression.release_gate import release_gate


THRESHOLDS = {
    "hard_thresholds": {
        "overall_pass_rate": 0.95,
        "critical_case_pass_rate": 0.99,
        "transcript_accuracy": 0.95,
        "hallucination_rate_max": 0.01,
    },
    "stratified_thresholds": {
        "variant_type_classification_accuracy": {
            "minimum": 0.95,
            "minimum_assessable_cases": 5,
        }
    },
    "regression_limits": {
        "max_overall_drop": 0.01,
        "max_classification_drop": 0.005,
        "max_variant_type_classification_drop": 0.005,
        "minimum_variant_type_assessable_cases": 5,
        "allow_new_critical_failures": False,
    },
}


def test_overall_drop_fails():
    report = compare_to_baseline(
        {"overall_pass_rate": 0.94, "critical_case_pass_rate": 1.0, "classification_accuracy": 1.0, "transcript_accuracy": 1.0, "hallucination_rate": 0.0, "critical_failures": 0},
        {"overall_pass_rate": 0.96, "classification_accuracy": 1.0, "critical_failures": 0},
        THRESHOLDS,
    )
    assert not report.passed


def test_critical_failures_increase_fails():
    report = compare_to_baseline(
        {"overall_pass_rate": 1.0, "critical_case_pass_rate": 1.0, "classification_accuracy": 1.0, "transcript_accuracy": 1.0, "hallucination_rate": 0.0, "critical_failures": 1},
        {"overall_pass_rate": 1.0, "classification_accuracy": 1.0, "critical_failures": 0},
        THRESHOLDS,
    )
    assert "critical failures increased" in report.failures


def test_hallucination_rate_fails():
    report = compare_to_baseline(
        {"overall_pass_rate": 1.0, "critical_case_pass_rate": 1.0, "classification_accuracy": 1.0, "transcript_accuracy": 1.0, "hallucination_rate": 0.02, "critical_failures": 0},
        None,
        THRESHOLDS,
    )
    assert not report.passed
    assert report.hard_threshold_checks["hallucination_rate_max"] is False


def test_hard_thresholds_are_independent_of_baseline():
    report = compare_to_baseline(
        {"overall_pass_rate": 0.94, "critical_case_pass_rate": 1.0, "classification_accuracy": 1.0, "transcript_accuracy": 1.0, "hallucination_rate": 0.0, "critical_failures": 0},
        {"overall_pass_rate": 0.50, "classification_accuracy": 0.50, "critical_failures": 0},
        THRESHOLDS,
    )

    assert report.hard_threshold_checks["overall_pass_rate"] is False
    assert "overall_pass_rate hard threshold failed" in report.failures
    assert not report.passed


def test_all_thresholds_pass():
    report = compare_to_baseline(
        {"overall_pass_rate": 1.0, "critical_case_pass_rate": 1.0, "classification_accuracy": 1.0, "transcript_accuracy": 1.0, "hallucination_rate": 0.0, "critical_failures": 0},
        {"overall_pass_rate": 1.0, "classification_accuracy": 1.0, "critical_failures": 0},
        THRESHOLDS,
    )
    assert release_gate(report) == 0
    assert report.hard_threshold_checks
    assert report.regression_checks


def test_variant_type_hard_threshold_fails_for_supported_cohort():
    report = compare_to_baseline(
        {
            "overall_pass_rate": 1.0,
            "critical_case_pass_rate": 1.0,
            "classification_accuracy": 1.0,
            "transcript_accuracy": 1.0,
            "hallucination_rate": 0.0,
            "critical_failures": 0,
            "accuracy_by_variant_type": {
                "snv": {"assessable_cases": 10, "classification_accuracy": 0.90},
            },
        },
        None,
        THRESHOLDS,
    )

    assert report.hard_threshold_checks["variant_type_classification_accuracy:snv"] is False
    assert "snv classification accuracy hard threshold failed" in report.failures


def test_variant_type_hard_threshold_skips_small_cohort():
    report = compare_to_baseline(
        {
            "overall_pass_rate": 1.0,
            "critical_case_pass_rate": 1.0,
            "classification_accuracy": 1.0,
            "transcript_accuracy": 1.0,
            "hallucination_rate": 0.0,
            "critical_failures": 0,
            "accuracy_by_variant_type": {
                "indel": {"assessable_cases": 1, "classification_accuracy": 0.0},
            },
        },
        None,
        THRESHOLDS,
    )

    assert "variant_type_classification_accuracy:indel" not in report.hard_threshold_checks
    assert report.passed


def test_variant_type_classification_regression_fails_for_supported_cohort():
    report = compare_to_baseline(
        {
            "overall_pass_rate": 1.0,
            "critical_case_pass_rate": 1.0,
            "classification_accuracy": 1.0,
            "transcript_accuracy": 1.0,
            "hallucination_rate": 0.0,
            "critical_failures": 0,
            "accuracy_by_variant_type": {
                "snv": {"assessable_cases": 10, "classification_accuracy": 0.98},
            },
        },
        {
            "overall_pass_rate": 1.0,
            "classification_accuracy": 1.0,
            "critical_failures": 0,
            "accuracy_by_variant_type": {
                "snv": {"assessable_cases": 10, "classification_accuracy": 1.0},
            },
        },
        THRESHOLDS,
    )

    assert report.regression_checks["max_variant_type_classification_drop:snv"] is False
    assert "snv classification accuracy regressed" in report.failures
