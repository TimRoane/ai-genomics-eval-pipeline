from __future__ import annotations

from genomics_eval.schemas import RegressionReport


def compare_to_baseline(
    current_metrics: dict,
    baseline_metrics: dict | None,
    thresholds: dict,
) -> RegressionReport:
    checks: dict[str, bool] = {}
    hard_threshold_checks: dict[str, bool] = {}
    regression_checks: dict[str, bool] = {}
    failures: list[str] = []
    hard_thresholds = thresholds.get("hard_thresholds", thresholds.get("minimums", {}))
    limits = thresholds.get("regression_limits", {})

    for metric, minimum in hard_thresholds.items():
        if metric.endswith("_max"):
            actual_metric = metric.removesuffix("_max")
            ok = current_metrics.get(actual_metric, 0) <= minimum
        else:
            ok = current_metrics.get(metric, 0) >= minimum
        hard_threshold_checks[metric] = ok
        checks[metric] = ok
        if not ok:
            failures.append(f"{metric} hard threshold failed")

    if baseline_metrics:
        overall_drop = baseline_metrics.get("overall_pass_rate", 0) - current_metrics.get("overall_pass_rate", 0)
        ok = overall_drop <= limits.get("max_overall_drop", 1.0)
        regression_checks["max_overall_drop"] = ok
        checks["max_overall_drop"] = ok
        if not ok:
            failures.append("overall pass rate regressed")

        class_drop = baseline_metrics.get("classification_accuracy", 0) - current_metrics.get("classification_accuracy", 0)
        ok = class_drop <= limits.get("max_classification_drop", 1.0)
        regression_checks["max_classification_drop"] = ok
        checks["max_classification_drop"] = ok
        if not ok:
            failures.append("classification accuracy regressed")

        if not limits.get("allow_new_critical_failures", True):
            ok = current_metrics.get("critical_failures", 0) <= baseline_metrics.get("critical_failures", 0)
            regression_checks["allow_new_critical_failures"] = ok
            checks["allow_new_critical_failures"] = ok
            if not ok:
                failures.append("critical failures increased")

    return RegressionReport(
        passed=not failures,
        current_metrics=current_metrics,
        baseline_metrics=baseline_metrics,
        hard_threshold_checks=hard_threshold_checks,
        regression_checks=regression_checks,
        checks=checks,
        failures=failures,
    )
