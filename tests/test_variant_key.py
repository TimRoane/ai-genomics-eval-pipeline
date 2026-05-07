from genomics_eval.normalization.variant_key import canonical_variant_key
from genomics_eval.normalization.vcf_normalizer import normalize_vcf_record, split_multiallelic_alt


def test_canonical_key_normalizes_chr_prefix():
    assert canonical_variant_key("GRCh38", "chr17", 43071077, "A", "T") == "GRCh38|17|43071077|A|T"
    assert canonical_variant_key("GRCh38", "17", 43071077, "A", "T") == "GRCh38|17|43071077|A|T"


def test_normalize_vcf_record_snv_and_indel():
    snv = normalize_vcf_record("chr17", 43071077, "A", "T", "GRCh38", "case")
    assert snv.normalized_key == "GRCh38|17|43071077|A|T"
    insertion = normalize_vcf_record("17", 43071077, "A", "AT", "GRCh38", "case")
    assert insertion.normalized_key == "GRCh38|17|43071077|A|AT"


def test_split_multiallelic_alt():
    records = split_multiallelic_alt({"chrom": "17", "pos": 43071077, "ref": "A", "alt": "T,G"})
    assert [record.alt for record in records] == ["T", "G"]
