from genomics_eval.schemas import EvalScore
from genomics_eval.scoring.aggregate import aggregate_scores


def make_score(
    case_id: str,
    *,
    gene_correct: bool = True,
    classification_correct: bool = True,
    condition_correct: bool = True,
    transcript_correct: bool | None = True,
    passed: bool = True,
    failure_modes: list[str] | None = None,
    tags: list[str] | None = None,
) -> EvalScore:
    return EvalScore(
        case_id=case_id,
        gene_correct=gene_correct,
        transcript_correct=transcript_correct,
        hgvs_correct=True,
        classification_correct=classification_correct,
        condition_correct=condition_correct,
        source_supported=None,
        hallucination_detected=False,
        passed=passed,
        severity="medium",
        failure_modes=failure_modes or [],
        tags=tags or [],
    )


def test_field_accuracies_exclude_output_quality_failures():
    metrics = aggregate_scores(
        [
            make_score("pass"),
            make_score("wrong-gene", gene_correct=False, passed=False, failure_modes=["WRONG_GENE"]),
            make_score(
                "parser-failure",
                gene_correct=False,
                classification_correct=False,
                condition_correct=False,
                transcript_correct=False,
                passed=False,
                failure_modes=["PARSER_FAILURE"],
            ),
        ]
    )

    assert metrics["overall_pass_rate"] == 0.3333
    assert metrics["gene_accuracy"] == 0.5
    assert metrics["classification_accuracy"] == 1.0
    assert metrics["condition_accuracy"] == 1.0
    assert metrics["transcript_accuracy"] == 1.0
    assert metrics["field_accuracy_counts"]["gene_accuracy"] == {
        "correct": 1,
        "assessable": 2,
        "incorrect": 1,
    }
    assert metrics["field_accuracy_counts"]["classification_accuracy"] == {
        "correct": 2,
        "assessable": 2,
        "incorrect": 0,
    }


def test_accuracy_metrics_are_stratified_by_variant_type():
    metrics = aggregate_scores(
        [
            make_score("snv-pass", tags=["snv"]),
            make_score(
                "snv-wrong-class",
                classification_correct=False,
                passed=False,
                failure_modes=["WRONG_CLASSIFICATION"],
                tags=["snv"],
            ),
            make_score("deletion-pass", tags=["deletion"]),
            make_score(
                "deletion-no-output",
                gene_correct=False,
                classification_correct=False,
                condition_correct=False,
                transcript_correct=False,
                passed=False,
                failure_modes=["NO_OUTPUT"],
                tags=["deletion"],
            ),
        ]
    )

    assert metrics["accuracy_by_variant_type"]["snv"] == {
        "assessable_cases": 2,
        "gene_accuracy": 1.0,
        "classification_accuracy": 0.5,
        "condition_accuracy": 1.0,
        "transcript_accuracy": 1.0,
        "field_accuracy_counts": {
            "gene_accuracy": {"correct": 2, "assessable": 2, "incorrect": 0},
            "classification_accuracy": {"correct": 1, "assessable": 2, "incorrect": 1},
            "condition_accuracy": {"correct": 2, "assessable": 2, "incorrect": 0},
            "transcript_accuracy": {"correct": 2, "assessable": 2, "incorrect": 0},
        },
    }
    assert metrics["accuracy_by_variant_type"]["deletion"]["assessable_cases"] == 1
    assert metrics["accuracy_by_variant_type"]["deletion"]["classification_accuracy"] == 1.0
