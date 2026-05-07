from genomics_eval.ai.model_client import MockModelClient
from genomics_eval.schemas import InputCase, VariantAnnotation


def test_mock_model_wrong_gene_injection():
    case = InputCase(
        case_id="negative",
        input_type="HGVS",
        question="q",
        expected_gene="PAH",
        expected_classification="Pathogenic",
        metadata={"mock_failure_modes": ["wrong_gene"]},
    )

    output = MockModelClient().generate(case, "prompt", VariantAnnotation(case_id="negative"))

    assert output.extracted_gene == "BRCA1"


def test_mock_model_parser_failure_injection():
    case = InputCase(
        case_id="negative",
        input_type="HGVS",
        question="q",
        expected_gene="TP53",
        expected_classification="Pathogenic",
        metadata={"mock_failure_modes": ["parser_failure"]},
    )

    output = MockModelClient().generate(case, "prompt", VariantAnnotation(case_id="negative"))

    assert output.parser_failure


def test_mock_model_no_output_injection():
    case = InputCase(
        case_id="negative",
        input_type="HGVS",
        question="q",
        expected_gene="CFTR",
        expected_classification="Pathogenic",
        metadata={"mock_failure_modes": ["no_output"]},
    )

    output = MockModelClient().generate(case, "prompt", VariantAnnotation(case_id="negative"))

    assert output.response_text == ""
