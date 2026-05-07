from __future__ import annotations

from pathlib import Path

from genomics_eval.normalization.variant_key import canonical_variant_key
from genomics_eval.schemas import NormalizedVariant, VariantAnnotation


def parse_info(info_string: str) -> dict[str, str]:
    info: dict[str, str] = {}
    for field in info_string.split(";"):
        if not field:
            continue
        if "=" in field:
            key, value = field.split("=", 1)
            info[key] = value.replace("%2C", ",")
        else:
            info[field] = "true"
    return info


class ClinVarAnnotator:
    def __init__(self, path: str | Path | None = None, assembly: str = "GRCh38") -> None:
        self.path = Path(path) if path else None
        self.assembly = assembly
        self.index: dict[str, VariantAnnotation] = {}
        if self.path:
            self.load_vcf(self.path)

    def load_vcf(self, path: str | Path) -> None:
        self.path = Path(path)
        self.index = {}
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip() or line.startswith("#"):
                    continue
                chrom, pos, _id, ref, alt, *_rest, info = line.rstrip("\n").split("\t")
                for alt_allele in alt.split(","):
                    key = canonical_variant_key(self.assembly, chrom, int(pos), ref, alt_allele)
                    parsed = parse_info(info)
                    gene = _gene_symbol(parsed.get("GENEINFO"))
                    hgvs_values = _split_info_list(parsed.get("CLNHGVS"))
                    self.index[key] = VariantAnnotation(
                        case_id="clinvar",
                        normalized_key=key,
                        gene_symbol=gene,
                        dbsnp_id=_rsid(parsed.get("RS") or _id),
                        clinvar_variation_id=parsed.get("ALLELEID"),
                        clinvar_clnsig=_clean(parsed.get("CLNSIG")),
                        clinvar_review_status=_clean(parsed.get("CLNREVSTAT")),
                        clinvar_condition=_clean(parsed.get("CLNDN")),
                        hgvs_c=[value for value in hgvs_values if ":c." in value],
                        hgvs_p=[value for value in hgvs_values if ":p." in value],
                        transcript_options=[value.split(":", 1)[0] for value in hgvs_values if ":" in value],
                        annotation_warnings=["ClinVar VCF is summary-level and limited to precisely located variants"],
                    )

    def build_index(self) -> dict[str, VariantAnnotation]:
        return self.index

    def annotate(self, normalized_variant: NormalizedVariant) -> VariantAnnotation:
        key = normalized_variant.normalized_key
        if key and key in self.index:
            found = self.index[key].model_copy(update={"case_id": normalized_variant.case_id})
            return found
        return VariantAnnotation(
            case_id=normalized_variant.case_id,
            normalized_key=key,
            gene_symbol=normalized_variant.gene_symbol,
            annotation_warnings=["No ClinVar VCF match; source is limited to precisely located variants"],
        )


def _clean(value: str | None) -> str | None:
    return value.replace("_", " ") if value else None


def _split_info_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.replace("|", ",").split(",") if part.strip()]


def _gene_symbol(value: str | None) -> str | None:
    if not value:
        return None
    return value.split(":", 1)[0]


def _rsid(value: str | None) -> str | None:
    if not value or value == ".":
        return None
    return value if value.startswith("rs") else f"rs{value}"
