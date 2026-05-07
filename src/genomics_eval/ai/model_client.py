from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Protocol

from genomics_eval.ai.prompt_builder import parse_model_json
from genomics_eval.io import read_jsonl
from genomics_eval.schemas import AIOutput, InputCase, VariantAnnotation


class BaseModelClient(Protocol):
    model_name: str
    prompt_version: str

    def generate(self, case: InputCase, prompt: str, annotation: VariantAnnotation | None = None) -> AIOutput:
        ...


class MockModelClient:
    model_name = "mock"
    prompt_version = "v1"

    def generate(self, case: InputCase, prompt: str, annotation: VariantAnnotation | None = None) -> AIOutput:
        requested_failures = set(case.metadata.get("mock_failure_modes") or [])
        if "parser_failure" in requested_failures:
            return parse_model_json(
                "not valid json",
                case_id=case.case_id,
                model_name=self.model_name,
                prompt_version=self.prompt_version,
            )
        if "no_output" in requested_failures:
            return AIOutput(
                case_id=case.case_id,
                model_name=self.model_name,
                prompt_version=self.prompt_version,
                response_text="",
            )

        classification = case.expected_classification
        if "VUS" in case.case_id or "NEGATIVE" in case.case_id:
            classification = "Pathogenic"
        payload = {
            "gene": case.expected_gene or (annotation.gene_symbol if annotation else None),
            "transcript": case.expected_transcript,
            "hgvs": case.expected_hgvs_c,
            "classification": classification,
            "condition": case.expected_condition,
            "explanation": "Deterministic demo answer from provided annotation context.",
            "limitations": ["classification depends on source/version"],
            "confidence": "medium",
            "cited_sources": ["ClinVar"] if annotation and annotation.clinvar_clnsig else [],
        }
        if "wrong_gene" in requested_failures:
            payload["gene"] = "BRCA1" if case.expected_gene != "BRCA1" else "TP53"
        if "wrong_transcript" in requested_failures:
            payload["transcript"] = "NM_000000.0"
        if "wrong_hgvs" in requested_failures:
            payload["hgvs"] = "NM_000000.0:c.1A>T"
        if "wrong_condition" in requested_failures:
            payload["condition"] = "not specified"
        if "hallucinated_source" in requested_failures:
            payload["cited_sources"] = list(payload["cited_sources"]) + ["LitVar"]
        if "missing_limitation" in requested_failures:
            payload["limitations"] = []
        return parse_model_json(
            json.dumps(payload),
            case_id=case.case_id,
            model_name=self.model_name,
            prompt_version=self.prompt_version,
        )


class OfflineModelClient:
    model_name = "offline"
    prompt_version = "v1"

    def __init__(self, outputs_path: str | Path) -> None:
        self.outputs = {row["case_id"]: row for row in read_jsonl(outputs_path)}

    def generate(self, case: InputCase, prompt: str, annotation: VariantAnnotation | None = None) -> AIOutput:
        row = self.outputs.get(case.case_id)
        if not row:
            return AIOutput(
                case_id=case.case_id,
                model_name=self.model_name,
                prompt_version=self.prompt_version,
                response_text="",
            )
        if "response_text" in row:
            return parse_model_json(row["response_text"], case.case_id, self.model_name, self.prompt_version)
        return AIOutput.model_validate(row)


class OpenAIModelClient:
    model_name = "openai"
    prompt_version = "v1"

    def __init__(self) -> None:
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is required for OpenAIModelClient")

    def generate(self, case: InputCase, prompt: str, annotation: VariantAnnotation | None = None) -> AIOutput:
        raise NotImplementedError("OpenAI generation is intentionally optional for this demo.")
