from pathlib import Path

from genomics_eval.io import read_jsonl


HGVS_PREFIXES = ("NM_", "NR_", "NC_", "NG_")


def test_demo_case_set_has_expanded_hgvs_examples():
    cases = read_jsonl(Path("data/raw/input_cases.jsonl"))
    hgvs_cases = [case for case in cases if case["input_type"] == "HGVS"]
    assert len(cases) >= 20
    assert len(hgvs_cases) >= 8


def test_hgvs_inputs_use_current_transcript_nomenclature_shape():
    for case in read_jsonl(Path("data/raw/input_cases.jsonl")):
        if case["input_type"] != "HGVS":
            continue
        hgvs = case["input_variant"]
        assert hgvs.startswith(HGVS_PREFIXES)
        assert ":c." in hgvs
        assert not hgvs.endswith("delAG")
        assert case["expected_hgvs_c"] == hgvs


def test_demo_case_set_has_negative_controls_for_failure_modes():
    cases = read_jsonl(Path("data/raw/input_cases.jsonl"))
    requested_modes = {
        mode
        for case in cases
        for mode in case.get("metadata", {}).get("mock_failure_modes", [])
    }

    assert requested_modes >= {
        "wrong_gene",
        "wrong_transcript",
        "wrong_hgvs",
        "wrong_condition",
        "hallucinated_source",
        "missing_limitation",
        "parser_failure",
        "no_output",
    }


def test_demo_case_set_has_large_positive_control_cohort():
    cases = read_jsonl(Path("data/raw/input_cases.jsonl"))
    positive_controls = [
        case
        for case in cases
        if "positive_control" in case.get("tags", [])
    ]

    assert len(positive_controls) >= 30
    assert all("mock_failure_modes" not in case.get("metadata", {}) for case in positive_controls)
