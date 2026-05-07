from pathlib import Path

import requests

from genomics_eval.normalization.hgvs_normalizer import VariantValidatorClient


def test_valid_hgvs_extracts_validated_hgvs(tmp_path, monkeypatch):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"validated_hgvs": ["NM_007294.4:c.68_69del"]}

    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: Response())
    client = VariantValidatorClient(cache_path=tmp_path / "cache.json", enabled=True)
    variant = client.normalize_hgvs("NM_007294.4:c.68_69delAG", "GRCh38", "case")
    assert variant.validated_hgvs == ["NM_007294.4:c.68_69del"]


def test_timeout_returns_warning(tmp_path, monkeypatch):
    def timeout(*args, **kwargs):
        raise requests.Timeout()

    monkeypatch.setattr(requests, "get", timeout)
    client = VariantValidatorClient(cache_path=tmp_path / "cache.json", enabled=True)
    variant = client.normalize_hgvs("bad", "GRCh38", "case")
    assert "timeout" in variant.warnings[0].lower()


def test_cache_reused(tmp_path, monkeypatch):
    cache = tmp_path / "cache.json"
    cache.write_text('{"GRCh38:NM_1.1:c.1A>T": {"validated_hgvs": ["NM_1.1:c.1A>T"]}}', encoding="utf-8")
    client = VariantValidatorClient(cache_path=cache, enabled=True)
    result = client.validate_hgvs("NM_1.1:c.1A>T", "GRCh38")
    assert result["from_cache"] is True
