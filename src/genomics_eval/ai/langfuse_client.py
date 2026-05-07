from __future__ import annotations

import os
from typing import Iterable

from genomics_eval.schemas import EvalScore, InputCase


class LangfuseAdapter:
    def __init__(self, enabled: bool = False, dataset_name: str = "genomics/variant-eval-demo") -> None:
        self.enabled = enabled and bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))
        self.dataset_name = dataset_name
        self.client = None
        if self.enabled:
            from langfuse import Langfuse

            self.client = Langfuse()

    def create_or_get_dataset(self, dataset_name: str | None = None):
        if not self.enabled:
            return None
        return self.client.get_dataset(dataset_name or self.dataset_name)

    def upload_cases(self, cases: Iterable[InputCase]) -> None:
        if not self.enabled:
            return
        dataset = self.create_or_get_dataset()
        for case in cases:
            dataset.create_item(input=case.model_dump(mode="json"), expected_output=case.model_dump(mode="json"))

    def log_generation(self, case_id: str, prompt: str, output: str) -> None:
        if not self.enabled:
            return
        self.client.generation(name=case_id, input=prompt, output=output)

    def log_scores(self, case_id: str, score: EvalScore) -> None:
        if not self.enabled:
            return
        self.client.score(name=f"{case_id}:passed", value=1.0 if score.passed else 0.0)
