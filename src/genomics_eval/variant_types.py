from __future__ import annotations

from genomics_eval.schemas import InputCase

VARIANT_TYPE_TAGS = ("snv", "deletion", "indel", "duplication")


def variant_type_from_tags(tags: list[str]) -> str:
    return next((tag for tag in VARIANT_TYPE_TAGS if tag in tags), "unclassified")


def classify_variant_type(case: InputCase) -> str:
    tagged_type = variant_type_from_tags(case.tags)
    if tagged_type != "unclassified":
        return tagged_type

    if case.input_type == "VCF_RECORD" and case.ref and case.alt:
        if len(case.ref) == len(case.alt) == 1:
            return "snv"
        if len(case.ref) > len(case.alt):
            return "deletion"
        if len(case.ref) != len(case.alt):
            return "indel"

    hgvs = case.input_variant or case.expected_hgvs_c or ""
    hgvs_lower = hgvs.lower()
    if "dup" in hgvs_lower:
        return "duplication"
    if "del" in hgvs_lower:
        return "deletion"
    if "ins" in hgvs_lower:
        return "indel"
    if ">" in hgvs:
        return "snv"

    return "unclassified"
