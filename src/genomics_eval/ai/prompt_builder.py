from __future__ import annotations

import json
from typing import Any

from genomics_eval.schemas import AIOutput, InputCase, VariantAnnotation


def build_prompt(case: InputCase, annotation: VariantAnnotation | None = None) -> str:
    annotation = annotation or VariantAnnotation(case_id=case.case_id)
    case_input = case.input_variant or f"{case.chrom}:{case.pos}:{case.ref}>{case.alt}"
    context = {
        "gene": annotation.gene_symbol,
        "clinvar_clnsig": annotation.clinvar_clnsig,
        "clinvar_review_status": annotation.clinvar_review_status,
        "clinvar_condition": annotation.clinvar_condition,
        "dbsnp_id": annotation.dbsnp_id,
        "hgvs_c": annotation.hgvs_c,
        "transcripts": annotation.transcript_options,
        "limitations": annotation.annotation_warnings,
    }
    return "\n".join(
        [
            "You are evaluating a genomic variant. Use only the provided annotation context.",
            "Do not invent disease associations, sources, or clinical significance.",
            "If evidence is insufficient or conflicting, say so.",
            "",
            f"Input: {case_input}",
            f"Annotation context: {json.dumps(context, sort_keys=True)}",
            f"Question: {case.question}",
            "",
            "Return JSON with: gene, transcript, hgvs, classification, condition, explanation, limitations, confidence, cited_sources.",
        ]
    )


def parse_model_json(
    response_text: str,
    case_id: str,
    model_name: str = "unknown",
    prompt_version: str = "v1",
) -> AIOutput:
    try:
        parsed: dict[str, Any] = json.loads(response_text)
    except json.JSONDecodeError:
        return AIOutput(
            case_id=case_id,
            model_name=model_name,
            prompt_version=prompt_version,
            response_text=response_text,
            parser_failure=True,
        )
    return AIOutput(
        case_id=case_id,
        model_name=model_name,
        prompt_version=prompt_version,
        response_text=response_text,
        extracted_gene=parsed.get("gene"),
        extracted_transcript=parsed.get("transcript"),
        extracted_hgvs=parsed.get("hgvs"),
        extracted_classification=parsed.get("classification"),
        extracted_condition=parsed.get("condition"),
        cited_sources=list(parsed.get("cited_sources") or []),
        explanation=parsed.get("explanation"),
        limitations=list(parsed.get("limitations") or []),
    )
