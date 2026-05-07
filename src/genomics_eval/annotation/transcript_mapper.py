from __future__ import annotations

import re
from typing import Any

from genomics_eval.schemas import VariantAnnotation


def get_transcript_options(annotation: VariantAnnotation | None = None, vv_response: dict | None = None) -> list[str]:
    options: list[str] = []
    if annotation:
        options.extend(annotation.transcript_options)
        options.extend(value.split(":", 1)[0] for value in annotation.hgvs_c if ":" in value)
    if vv_response:
        options.extend(re.findall(r"\bN[MR]_\d+\.\d+", str(vv_response)))
    return sorted(set(option for option in options if option))


def select_transcript(
    options: list[str],
    expected_transcript: str | None = None,
    policy: str = "expected_or_mane_or_first",
) -> tuple[str | None, list[str]]:
    warnings: list[str] = []
    if expected_transcript and expected_transcript in options:
        return expected_transcript, warnings
    if len(options) > 1:
        warnings.append("TRANSCRIPT_AMBIGUITY")
    if not options:
        return None, warnings
    if policy == "expected_or_mane_or_first":
        mane = [option for option in options if option.startswith("NM_")]
        return (mane[0] if mane else options[0]), warnings
    return options[0], warnings
