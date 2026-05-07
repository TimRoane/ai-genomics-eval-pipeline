from genomics_eval.schemas import AIOutput, InputCase, VariantAnnotation
from genomics_eval.scoring.field_scorers import normalize_classification, score_case


def test_normalize_classification_aliases():
    assert normalize_classification("VUS") == "Uncertain significance"


def test_correct_gene_classification_passes():
    case = InputCase(
        case_id="c",
        input_type="VCF_RECORD",
        question="q",
        expected_gene="BRCA1",
        expected_classification="Pathogenic",
        expected_condition="Hereditary breast and ovarian cancer syndrome",
    )
    output = AIOutput(
        case_id="c",
        model_name="mock",
        prompt_version="v1",
        response_text="{}",
        extracted_gene="BRCA1",
        extracted_classification="Pathogenic",
        extracted_condition="breast ovarian cancer syndrome",
        limitations=["classification depends on source/version"],
    )
    score = score_case(case, VariantAnnotation(case_id="c"), output)
    assert score.passed


def test_wrong_classification_fails():
    case = InputCase(case_id="c", input_type="VCF_RECORD", question="q", expected_gene="BRCA1", expected_classification="Benign")
    output = AIOutput(case_id="c", model_name="mock", prompt_version="v1", response_text="{}", extracted_gene="BRCA1", extracted_classification="Pathogenic", limitations=["x"])
    score = score_case(case, VariantAnnotation(case_id="c"), output)
    assert "WRONG_CLASSIFICATION" in score.failure_modes


def test_missing_transcript_fails_only_when_required():
    case = InputCase(case_id="c", input_type="HGVS", question="q", expected_gene="BRCA1", expected_transcript="NM_1.1", expected_classification="Pathogenic")
    output = AIOutput(case_id="c", model_name="mock", prompt_version="v1", response_text="{}", extracted_gene="BRCA1", extracted_classification="Pathogenic", limitations=["x"])
    score = score_case(case, VariantAnnotation(case_id="c"), output)
    assert "WRONG_TRANSCRIPT" in score.failure_modes


def test_vus_overcalled_pathogenic_failure():
    case = InputCase(case_id="c", input_type="VCF_RECORD", question="q", expected_gene="APOE", expected_classification="Uncertain significance")
    output = AIOutput(case_id="c", model_name="mock", prompt_version="v1", response_text="{}", extracted_gene="APOE", extracted_classification="Pathogenic", limitations=["x"])
    score = score_case(case, VariantAnnotation(case_id="c"), output)
    assert "OVERCONFIDENT_VUS" in score.failure_modes


def test_parser_failure_fails():
    case = InputCase(case_id="c", input_type="VCF_RECORD", question="q", expected_gene="APOE", expected_classification="Benign")
    output = AIOutput(case_id="c", model_name="mock", prompt_version="v1", response_text="not json", parser_failure=True)
    score = score_case(case, VariantAnnotation(case_id="c"), output)
    assert score.failure_modes == ["PARSER_FAILURE"]


def test_wrong_gene_fails():
    case = InputCase(case_id="c", input_type="HGVS", question="q", expected_gene="PAH", expected_classification="Pathogenic")
    output = AIOutput(case_id="c", model_name="mock", prompt_version="v1", response_text="{}", extracted_gene="BRCA1", extracted_classification="Pathogenic", limitations=["x"])
    score = score_case(case, VariantAnnotation(case_id="c"), output)
    assert "WRONG_GENE" in score.failure_modes


def test_hgvs_mismatch_fails():
    case = InputCase(
        case_id="c",
        input_type="HGVS",
        question="q",
        expected_gene="GJB2",
        expected_hgvs_c="NM_004004.6:c.35del",
        expected_classification="Pathogenic",
    )
    output = AIOutput(
        case_id="c",
        model_name="mock",
        prompt_version="v1",
        response_text="{}",
        extracted_gene="GJB2",
        extracted_hgvs="NM_000000.0:c.1A>T",
        extracted_classification="Pathogenic",
        limitations=["x"],
    )
    score = score_case(case, VariantAnnotation(case_id="c"), output)
    assert "HGVS_MISMATCH" in score.failure_modes


def test_disease_mapping_error_fails():
    case = InputCase(
        case_id="c",
        input_type="VCF_RECORD",
        question="q",
        expected_gene="F5",
        expected_classification="Pathogenic",
        expected_condition="Thrombophilia due to activated protein C resistance",
    )
    output = AIOutput(
        case_id="c",
        model_name="mock",
        prompt_version="v1",
        response_text="{}",
        extracted_gene="F5",
        extracted_classification="Pathogenic",
        extracted_condition="not specified",
        limitations=["x"],
    )
    score = score_case(case, VariantAnnotation(case_id="c"), output)
    assert "DISEASE_MAPPING_ERROR" in score.failure_modes


def test_hallucinated_source_fails():
    case = InputCase(case_id="c", input_type="VCF_RECORD", question="q", expected_gene="HFE", expected_classification="Pathogenic")
    output = AIOutput(
        case_id="c",
        model_name="mock",
        prompt_version="v1",
        response_text="{}",
        extracted_gene="HFE",
        extracted_classification="Pathogenic",
        cited_sources=["ClinVar", "LitVar"],
        limitations=["x"],
    )
    annotation = VariantAnnotation(case_id="c", clinvar_clnsig="Pathogenic")
    score = score_case(case, annotation, output)
    assert "HALLUCINATED_SOURCE" in score.failure_modes


def test_missing_limitation_fails():
    case = InputCase(case_id="c", input_type="HGVS", question="q", expected_gene="LDLR", expected_classification="Pathogenic")
    output = AIOutput(
        case_id="c",
        model_name="mock",
        prompt_version="v1",
        response_text="{}",
        extracted_gene="LDLR",
        extracted_classification="Pathogenic",
        limitations=[],
    )
    score = score_case(case, VariantAnnotation(case_id="c"), output)
    assert "MISSING_LIMITATION" in score.failure_modes


def test_no_output_fails():
    case = InputCase(case_id="c", input_type="HGVS", question="q", expected_gene="CFTR", expected_classification="Pathogenic")
    output = AIOutput(case_id="c", model_name="mock", prompt_version="v1", response_text="")
    score = score_case(case, VariantAnnotation(case_id="c"), output)
    assert score.failure_modes == ["NO_OUTPUT"]
