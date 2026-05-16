from __future__ import annotations

from collections import Counter, defaultdict

from genomics_eval.schemas import EvalScore
from genomics_eval.variant_types import variant_type_from_tags

OUTPUT_QUALITY_FAILURES = {"NO_OUTPUT", "PARSER_FAILURE"}


def aggregate_scores(scores: list[EvalScore]) -> dict:
    if not scores:
        return {}
    total = len(scores)
    critical = [score for score in scores if score.severity == "critical"]
    content_scores = [score for score in scores if _has_assessable_content(score)]
    failures = Counter(mode for score in scores for mode in score.failure_modes)
    tag_totals: dict[str, int] = defaultdict(int)
    tag_passes: dict[str, int] = defaultdict(int)
    for score in scores:
        for tag in score.tags:
            tag_totals[tag] += 1
            tag_passes[tag] += int(score.passed)
    return {
        "overall_pass_rate": _rate(sum(score.passed for score in scores), total),
        "critical_case_pass_rate": _rate(sum(score.passed for score in critical), len(critical)),
        "gene_accuracy": _bool_rate([score.gene_correct for score in content_scores]),
        "classification_accuracy": _bool_rate([score.classification_correct for score in content_scores]),
        "condition_accuracy": _bool_rate([score.condition_correct for score in content_scores]),
        "transcript_accuracy": _optional_rate([score.transcript_correct for score in content_scores]),
        "field_accuracy_counts": _field_accuracy_counts(content_scores),
        "accuracy_by_variant_type": _accuracy_by_variant_type(content_scores),
        "hallucination_rate": _rate(sum(score.hallucination_detected for score in scores), total),
        "failures_by_mode": dict(failures),
        "pass_rate_by_tag": {tag: _rate(tag_passes[tag], count) for tag, count in tag_totals.items()},
        "critical_failures": sum((not score.passed) and score.severity == "critical" for score in scores),
    }


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 1.0


def _optional_rate(values: list[bool | None]) -> float:
    present = [value for value in values if value is not None]
    return _rate(sum(bool(value) for value in present), len(present))


def _bool_rate(values: list[bool]) -> float:
    return _rate(sum(values), len(values))


def _has_assessable_content(score: EvalScore) -> bool:
    return not (set(score.failure_modes) & OUTPUT_QUALITY_FAILURES)


def _field_accuracy_counts(scores: list[EvalScore]) -> dict[str, dict[str, int]]:
    return {
        "gene_accuracy": _required_count([score.gene_correct for score in scores]),
        "classification_accuracy": _required_count([score.classification_correct for score in scores]),
        "condition_accuracy": _required_count([score.condition_correct for score in scores]),
        "transcript_accuracy": _optional_count([score.transcript_correct for score in scores]),
    }


def _accuracy_by_variant_type(scores: list[EvalScore]) -> dict[str, dict]:
    grouped_scores: dict[str, list[EvalScore]] = defaultdict(list)
    for score in scores:
        variant_type = score.variant_type if score.variant_type != "unclassified" else variant_type_from_tags(score.tags)
        grouped_scores[variant_type].append(score)

    return {
        variant_type: {
            "assessable_cases": len(group),
            "gene_accuracy": _bool_rate([score.gene_correct for score in group]),
            "classification_accuracy": _bool_rate([score.classification_correct for score in group]),
            "condition_accuracy": _bool_rate([score.condition_correct for score in group]),
            "transcript_accuracy": _optional_rate([score.transcript_correct for score in group]),
            "field_accuracy_counts": _field_accuracy_counts(group),
        }
        for variant_type, group in sorted(grouped_scores.items())
    }


def _required_count(values: list[bool]) -> dict[str, int]:
    return {
        "correct": sum(values),
        "assessable": len(values),
        "incorrect": len(values) - sum(values),
    }


def _optional_count(values: list[bool | None]) -> dict[str, int]:
    present = [value for value in values if value is not None]
    correct = sum(bool(value) for value in present)
    return {
        "correct": correct,
        "assessable": len(present),
        "incorrect": len(present) - correct,
    }
