from pathlib import Path


EXAMPLE_VCF = Path("data/raw/example.vcf")


def read_vcf_lines() -> list[str]:
    return EXAMPLE_VCF.read_text(encoding="utf-8").splitlines()


def test_example_vcf_is_modern_synthetic_fixture():
    lines = read_vcf_lines()

    assert lines[0] == "##fileformat=VCFv4.3"
    assert "##source=ai-genomics-eval-pipeline-synthetic-fixture" in lines
    assert "##reference=GRCh38" in lines


def test_example_vcf_has_required_metadata_sections():
    lines = read_vcf_lines()
    prefixes = {
        "contig": "##contig=<",
        "info": "##INFO=<",
        "filter": "##FILTER=<",
        "format": "##FORMAT=<",
    }

    for prefix in prefixes.values():
        assert any(line.startswith(prefix) for line in lines)

    for info_id in ["GENE", "CLNSIG", "CLNREVSTAT", "CLNDN", "RS", "SYNTHETIC_REASON"]:
        assert any(line.startswith(f"##INFO=<ID={info_id},") for line in lines)

    for format_id in ["GT", "DP", "AD", "GQ"]:
        assert any(line.startswith(f"##FORMAT=<ID={format_id},") for line in lines)


def test_example_vcf_has_sample_column_and_consistent_record_width():
    lines = read_vcf_lines()
    header = next(line for line in lines if line.startswith("#CHROM"))
    header_fields = header.split("\t")

    assert header_fields[:9] == ["#CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO", "FORMAT"]
    assert header_fields[9:] == ["demo_case"]

    records = [line for line in lines if line and not line.startswith("#")]
    assert records
    assert all(len(record.split("\t")) == len(header_fields) for record in records)


def test_example_vcf_contains_known_synthetic_error_states():
    records = [line for line in read_vcf_lines() if line and not line.startswith("#")]

    assert any("\tLowQual\t" in record for record in records)
    assert any("SYNTHETIC_REASON=known_negative_control" in record for record in records)
    assert any("SYNTHETIC_REASON=known_low_quality_error_state" in record for record in records)
