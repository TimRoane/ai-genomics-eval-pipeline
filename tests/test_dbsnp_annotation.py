from pathlib import Path

from genomics_eval.annotation.dbsnp import DbSnpAnnotator
from genomics_eval.normalization.vcf_normalizer import normalize_vcf_record


def test_known_key_returns_rsid():
    annotator = DbSnpAnnotator(Path("data/reference/dbsnp_subset.tsv"))
    variant = normalize_vcf_record("19", 44908684, "T", "C", "GRCh38", "case")
    assert annotator.annotate(variant) == "rs429358"


def test_unknown_key_returns_none():
    annotator = DbSnpAnnotator(Path("data/reference/dbsnp_subset.tsv"))
    variant = normalize_vcf_record("1", 1, "A", "T", "GRCh38", "case")
    assert annotator.annotate(variant) is None
