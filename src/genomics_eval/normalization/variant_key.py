from __future__ import annotations


def normalize_chrom(chrom: str | int | None) -> str | None:
    if chrom is None:
        return None
    value = str(chrom).strip()
    if value.lower().startswith("chr"):
        value = value[3:]
    return value.upper() if value.upper() in {"X", "Y", "M", "MT"} else value


def canonical_variant_key(
    assembly: str,
    chrom: str | int,
    pos: int,
    ref: str,
    alt: str,
) -> str:
    return f"{assembly}|{normalize_chrom(chrom)}|{int(pos)}|{ref.upper()}|{alt.upper()}"
