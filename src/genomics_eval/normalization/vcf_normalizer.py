from __future__ import annotations

from dataclasses import dataclass

from genomics_eval.normalization.variant_key import canonical_variant_key, normalize_chrom
from genomics_eval.schemas import NormalizedVariant


@dataclass(frozen=True)
class VcfAllele:
    chrom: str
    pos: int
    ref: str
    alt: str


def split_multiallelic_alt(record: dict | VcfAllele) -> list[VcfAllele]:
    if isinstance(record, dict):
        chrom = str(record["chrom"])
        pos = int(record["pos"])
        ref = str(record["ref"])
        alt = str(record["alt"])
    else:
        chrom, pos, ref, alt = record.chrom, record.pos, record.ref, record.alt
    return [VcfAllele(chrom=chrom, pos=pos, ref=ref, alt=part.strip()) for part in alt.split(",")]


def normalize_vcf_record(
    chrom: str,
    pos: int,
    ref: str,
    alt: str,
    assembly: str,
    case_id: str = "unknown",
) -> NormalizedVariant:
    clean_chrom = normalize_chrom(chrom)
    clean_ref = ref.upper()
    clean_alt = alt.upper()
    key = canonical_variant_key(assembly, clean_chrom or chrom, pos, clean_ref, clean_alt)
    return NormalizedVariant(
        case_id=case_id,
        assembly=assembly,
        chrom=clean_chrom,
        pos=int(pos),
        ref=clean_ref,
        alt=clean_alt,
        normalized_key=key,
    )
