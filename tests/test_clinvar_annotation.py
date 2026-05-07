from pathlib import Path

from genomics_eval.annotation.clinvar import ClinVarAnnotator, parse_info
from genomics_eval.normalization.vcf_normalizer import normalize_vcf_record


FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_info_geneinfo():
    parsed = parse_info("CLNSIG=Pathogenic;GENEINFO=BRCA1:672")
    assert parsed["GENEINFO"] == "BRCA1:672"


def test_clinvar_match_returns_fields():
    annotator = ClinVarAnnotator(FIXTURES / "tiny_clinvar.vcf")
    variant = normalize_vcf_record("17", 43071077, "A", "AT", "GRCh38", "case")
    annotation = annotator.annotate(variant)
    assert annotation.clinvar_clnsig == "Pathogenic/Likely pathogenic"
    assert annotation.clinvar_review_status == "criteria provided multiple submitters no conflicts"
    assert annotation.gene_symbol == "BRCA1"
    assert annotation.transcript_options == ["NM_007294.4", "NM_007299.4"]


def test_clinvar_no_match_warns():
    annotator = ClinVarAnnotator(FIXTURES / "tiny_clinvar.vcf")
    variant = normalize_vcf_record("1", 1, "A", "T", "GRCh38", "case")
    annotation = annotator.annotate(variant)
    assert annotation.clinvar_clnsig is None
    assert annotation.annotation_warnings
