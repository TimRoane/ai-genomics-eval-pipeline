from __future__ import annotations

import re

from genomics_eval.schemas import AIOutput, EvalScore, InputCase, VariantAnnotation
from genomics_eval.variant_types import classify_variant_type

CLASSIFICATION_ALIASES = {
    "pathogenic": "Pathogenic",
    "likely pathogenic": "Likely pathogenic",
    "benign": "Benign",
    "likely benign": "Likely benign",
    "vus": "Uncertain significance",
    "variant of uncertain significance": "Uncertain significance",
    "uncertain significance": "Uncertain significance",
    "uncertain_significance": "Uncertain significance",
}


def normalize_classification(text: str | None) -> str | None:
    if not text:
        return None
    clean = re.sub(r"[_/]+", " ", text).strip().lower()
    return CLASSIFICATION_ALIASES.get(clean, text.replace("_", " ").strip())


def fuzzy_condition_match(expected: str | None, actual: str | None) -> bool:
    if not expected:
        return True
    if not actual:
        return False
    expected_tokens = _tokens(expected)
    actual_tokens = _tokens(actual)
    if not expected_tokens:
        return True
    return len(expected_tokens & actual_tokens) / len(expected_tokens) >= 0.6


def score_case(case: InputCase, annotation: VariantAnnotation | None, ai_output: AIOutput) -> EvalScore:
    failure_modes: list[str] = []
    if not ai_output.response_text:
        failure_modes.append("NO_OUTPUT")
    if ai_output.parser_failure:
        failure_modes.append("PARSER_FAILURE")
    if failure_modes:
        return EvalScore(
            case_id=case.case_id,
            variant_type=classify_variant_type(case),
            gene_correct=case.expected_gene is None,
            transcript_correct=False if case.expected_transcript else None,
            hgvs_correct=False if case.expected_hgvs_c else None,
            classification_correct=case.expected_classification is None,
            condition_correct=case.expected_condition is None,
            source_supported=None,
            hallucination_detected=False,
            passed=False,
            severity=case.severity,
            failure_modes=sorted(set(failure_modes)),
            tags=case.tags,
        )

    gene_correct = _same(case.expected_gene, ai_output.extracted_gene)
    if not gene_correct:
        failure_modes.append("WRONG_GENE")

    expected_class = normalize_classification(case.expected_classification)
    actual_class = normalize_classification(ai_output.extracted_classification)
    classification_correct = expected_class == actual_class
    if not classification_correct:
        failure_modes.append("WRONG_CLASSIFICATION")
    if expected_class in {"Uncertain significance", "Benign", "Likely benign"} and actual_class in {"Pathogenic", "Likely pathogenic"}:
        failure_modes.append("OVERCONFIDENT_VUS")

    transcript_correct: bool | None = None
    if case.expected_transcript:
        transcript_correct = _same(case.expected_transcript, ai_output.extracted_transcript)
        if not transcript_correct:
            failure_modes.append("WRONG_TRANSCRIPT")

    hgvs_correct: bool | None = None
    if case.expected_hgvs_c:
        hgvs_correct = _same(_strip_hgvs(case.expected_hgvs_c), _strip_hgvs(ai_output.extracted_hgvs))
        if not hgvs_correct:
            failure_modes.append("HGVS_MISMATCH")

    condition_correct = fuzzy_condition_match(case.expected_condition, ai_output.extracted_condition)
    if not condition_correct:
        failure_modes.append("DISEASE_MAPPING_ERROR")

    allowed_sources = set()
    if annotation and annotation.clinvar_clnsig:
        allowed_sources.add("ClinVar")
    if annotation and annotation.dbsnp_id:
        allowed_sources.add("dbSNP")
    hallucinated_sources = [source for source in ai_output.cited_sources if source not in allowed_sources]
    source_supported = not hallucinated_sources if ai_output.cited_sources else None
    hallucination_detected = bool(hallucinated_sources)
    if hallucination_detected:
        failure_modes.append("HALLUCINATED_SOURCE")

    if actual_class and not ai_output.limitations:
        failure_modes.append("MISSING_LIMITATION")

    passed = not failure_modes
    return EvalScore(
        case_id=case.case_id,
        variant_type=classify_variant_type(case),
        gene_correct=gene_correct,
        transcript_correct=transcript_correct,
        hgvs_correct=hgvs_correct,
        classification_correct=classification_correct,
        condition_correct=condition_correct,
        source_supported=source_supported,
        hallucination_detected=hallucination_detected,
        passed=passed,
        severity=case.severity,
        failure_modes=sorted(set(failure_modes)),
        tags=case.tags,
    )


def _same(expected: str | None, actual: str | None) -> bool:
    if expected is None:
        return True
    return (actual or "").strip().lower() == expected.strip().lower()


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.lower().replace("_", " "))) - {"and", "or", "the", "of"}


def _strip_hgvs(value: str | None) -> str | None:
    if value is None:
        return None
    return value.replace("delAG", "del").strip()
