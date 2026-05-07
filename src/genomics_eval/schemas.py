from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class InputCase(BaseModel):
    case_id: str
    input_type: str
    assembly: str = "GRCh38"
    question: str
    input_variant: str | None = None
    chrom: str | None = None
    pos: int | None = None
    ref: str | None = None
    alt: str | None = None
    expected_gene: str | None = None
    expected_transcript: str | None = None
    expected_hgvs_c: str | None = None
    expected_classification: str | None = None
    expected_condition: str | None = None
    expected_dbsnp: str | None = None
    expected_clinvar_review_status_min: str | None = None
    tags: list[str] = Field(default_factory=list)
    severity: str = "medium"
    metadata: dict[str, Any] = Field(default_factory=dict)


class NormalizedVariant(BaseModel):
    case_id: str
    assembly: str
    chrom: str | None = None
    pos: int | None = None
    ref: str | None = None
    alt: str | None = None
    normalized_key: str | None = None
    input_hgvs: str | None = None
    validated_hgvs: list[str] = Field(default_factory=list)
    selected_transcript: str | None = None
    gene_symbol: str | None = None
    warnings: list[str] = Field(default_factory=list)


class VariantAnnotation(BaseModel):
    case_id: str
    normalized_key: str | None = None
    gene_symbol: str | None = None
    dbsnp_id: str | None = None
    clinvar_variation_id: str | None = None
    clinvar_clnsig: str | None = None
    clinvar_review_status: str | None = None
    clinvar_condition: str | None = None
    hgvs_c: list[str] = Field(default_factory=list)
    hgvs_p: list[str] = Field(default_factory=list)
    transcript_options: list[str] = Field(default_factory=list)
    annotation_warnings: list[str] = Field(default_factory=list)


class AIOutput(BaseModel):
    case_id: str
    model_name: str
    prompt_version: str
    response_text: str
    extracted_gene: str | None = None
    extracted_transcript: str | None = None
    extracted_hgvs: str | None = None
    extracted_classification: str | None = None
    extracted_condition: str | None = None
    cited_sources: list[str] = Field(default_factory=list)
    explanation: str | None = None
    limitations: list[str] = Field(default_factory=list)
    parser_failure: bool = False


class EvalScore(BaseModel):
    case_id: str
    gene_correct: bool
    transcript_correct: bool | None = None
    hgvs_correct: bool | None = None
    classification_correct: bool
    condition_correct: bool
    source_supported: bool | None = None
    hallucination_detected: bool
    passed: bool
    severity: str
    failure_modes: list[str] = Field(default_factory=list)
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)


class RegressionReport(BaseModel):
    passed: bool
    current_metrics: dict[str, Any]
    baseline_metrics: dict[str, Any] | None = None
    hard_threshold_checks: dict[str, bool] = Field(default_factory=dict)
    regression_checks: dict[str, bool] = Field(default_factory=dict)
    checks: dict[str, bool] = Field(default_factory=dict)
    failures: list[str] = Field(default_factory=list)
