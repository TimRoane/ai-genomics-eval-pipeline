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
    stratified_thresholds = thresholds.get("stratified_thresholds", {})
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

    _check_variant_type_classification_hard_thresholds(
        current_metrics,
        stratified_thresholds.get("variant_type_classification_accuracy", {}),
        hard_threshold_checks,
        checks,
        failures,
    )

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

        _check_variant_type_classification_regressions(
            current_metrics,
            baseline_metrics,
            limits,
            regression_checks,
            checks,
            failures,
        )

    return RegressionReport(
        passed=not failures,
        current_metrics=current_metrics,
        baseline_metrics=baseline_metrics,
        hard_threshold_checks=hard_threshold_checks,
        regression_checks=regression_checks,
        checks=checks,
        failures=failures,
    )


def _check_variant_type_classification_hard_thresholds(
    current_metrics: dict,
    config: dict,
    hard_threshold_checks: dict[str, bool],
    checks: dict[str, bool],
    failures: list[str],
) -> None:
    if not config:
        return

    minimum = config.get("minimum", 0.0)
    minimum_assessable_cases = config.get("minimum_assessable_cases", 0)
    for variant_type, metrics in sorted(current_metrics.get("accuracy_by_variant_type", {}).items()):
        if metrics.get("assessable_cases", 0) < minimum_assessable_cases:
            continue
        ok = metrics.get("classification_accuracy", 0) >= minimum
        check_name = f"variant_type_classification_accuracy:{variant_type}"
        hard_threshold_checks[check_name] = ok
        checks[check_name] = ok
        if not ok:
            failures.append(f"{variant_type} classification accuracy hard threshold failed")


def _check_variant_type_classification_regressions(
    current_metrics: dict,
    baseline_metrics: dict,
    limits: dict,
    regression_checks: dict[str, bool],
    checks: dict[str, bool],
    failures: list[str],
) -> None:
    if "max_variant_type_classification_drop" not in limits:
        return

    maximum_drop = limits["max_variant_type_classification_drop"]
    minimum_assessable_cases = limits.get("minimum_variant_type_assessable_cases", 0)
    current_by_type = current_metrics.get("accuracy_by_variant_type", {})
    baseline_by_type = baseline_metrics.get("accuracy_by_variant_type", {})
    for variant_type in sorted(set(current_by_type) & set(baseline_by_type)):
        current = current_by_type[variant_type]
        baseline = baseline_by_type[variant_type]
        if min(current.get("assessable_cases", 0), baseline.get("assessable_cases", 0)) < minimum_assessable_cases:
            continue
        drop = baseline.get("classification_accuracy", 0) - current.get("classification_accuracy", 0)
        ok = drop <= maximum_drop
        check_name = f"max_variant_type_classification_drop:{variant_type}"
        regression_checks[check_name] = ok
        checks[check_name] = ok
        if not ok:
            failures.append(f"{variant_type} classification accuracy regressed")
