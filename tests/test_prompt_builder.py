from genomics_eval.ai.prompt_builder import build_prompt, parse_model_json
from genomics_eval.schemas import InputCase, VariantAnnotation


def test_prompt_includes_variant_review_status_and_guardrail():
    case = InputCase(case_id="c", input_type="HGVS", input_variant="NM_1.1:c.1A>T", question="Interpret?")
    annotation = VariantAnnotation(case_id="c", clinvar_review_status="criteria provided")
    prompt = build_prompt(case, annotation)
    assert "NM_1.1:c.1A>T" in prompt
    assert "criteria provided" in prompt
    assert "Do not invent" in prompt


def test_parser_handles_valid_json():
    output = parse_model_json('{"gene":"BRCA1","classification":"Pathogenic"}', "c")
    assert output.extracted_gene == "BRCA1"
    assert not output.parser_failure


def test_parser_handles_invalid_json():
    output = parse_model_json("not json", "c")
    assert output.parser_failure
