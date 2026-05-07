from genomics_eval.annotation.transcript_mapper import get_transcript_options, select_transcript
from genomics_eval.schemas import VariantAnnotation


def test_expected_transcript_selected():
    selected, warnings = select_transcript(["NM_1.1", "NM_2.1"], expected_transcript="NM_2.1")
    assert selected == "NM_2.1"
    assert warnings == []


def test_multiple_transcripts_flag_ambiguity():
    selected, warnings = select_transcript(["NM_1.1", "NM_2.1"])
    assert selected == "NM_1.1"
    assert "TRANSCRIPT_AMBIGUITY" in warnings


def test_get_transcript_options_from_annotation():
    annotation = VariantAnnotation(case_id="c", hgvs_c=["NM_007294.4:c.68_69del"])
    assert get_transcript_options(annotation) == ["NM_007294.4"]
