from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

from genomics_eval.schemas import NormalizedVariant


class VariantValidatorClient:
    def __init__(
        self,
        base_url: str = "https://rest.variantvalidator.org",
        endpoint_template: str = "/VariantValidator/variantvalidator/{assembly}/{hgvs}/all?content-type=application/json",
        timeout_seconds: int = 20,
        cache_path: str | Path = "data/cache/variantvalidator_cache.json",
        enabled: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.endpoint_template = endpoint_template
        self.timeout_seconds = timeout_seconds
        self.cache_path = Path(cache_path)
        self.enabled = enabled
        self.cache: dict[str, Any] = {}
        if self.cache_path.exists():
            self.cache = json.loads(self.cache_path.read_text(encoding="utf-8"))

    def _cache_key(self, hgvs: str, assembly: str) -> str:
        return f"{assembly}:{hgvs}"

    def _write_cache(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(self.cache, indent=2, sort_keys=True), encoding="utf-8")

    def validate_hgvs(self, hgvs: str, assembly: str) -> dict:
        key = self._cache_key(hgvs, assembly)
        if key in self.cache:
            return {"from_cache": True, "data": self.cache[key]}
        if not self.enabled:
            return {"error": "VariantValidator disabled", "data": None}
        path = self.endpoint_template.format(assembly=quote(assembly), hgvs=quote(hgvs, safe=""))
        try:
            response = requests.get(f"{self.base_url}{path}", timeout=self.timeout_seconds)
            response.raise_for_status()
            data = response.json()
        except requests.Timeout:
            return {"error": "VariantValidator timeout", "data": None}
        except requests.RequestException as exc:
            return {"error": f"VariantValidator request failed: {exc}", "data": None}
        except ValueError:
            return {"error": "VariantValidator returned non-JSON response", "data": None}
        self.cache[key] = data
        self._write_cache()
        return {"from_cache": False, "data": data}

    def normalize_hgvs(self, hgvs: str, assembly: str, case_id: str = "unknown") -> NormalizedVariant:
        result = self.validate_hgvs(hgvs, assembly)
        variant = NormalizedVariant(case_id=case_id, assembly=assembly, input_hgvs=hgvs)
        if result.get("error"):
            variant.warnings.append(str(result["error"]))
            return variant
        data = result.get("data") or {}
        validated = _extract_hgvs_strings(data)
        variant.validated_hgvs = validated or [hgvs]
        variant.selected_transcript = _first_transcript(variant.validated_hgvs)
        return variant


def _extract_hgvs_strings(data: Any) -> list[str]:
    values: list[str] = []
    if isinstance(data, dict):
        for key, value in data.items():
            lowered = str(key).lower()
            if lowered in {"hgvs", "hgvs_c", "submitted_variant", "validated_hgvs"}:
                if isinstance(value, str):
                    values.append(value)
                elif isinstance(value, list):
                    values.extend(str(item) for item in value if item)
            values.extend(_extract_hgvs_strings(value))
    elif isinstance(data, list):
        for item in data:
            values.extend(_extract_hgvs_strings(item))
    return sorted(set(values))


def _first_transcript(hgvs_values: list[str]) -> str | None:
    for value in hgvs_values:
        if ":" in value:
            return value.split(":", 1)[0]
    return None


def normalize_hgvs(hgvs: str, assembly: str, case_id: str = "unknown") -> NormalizedVariant:
    client = VariantValidatorClient(enabled=False)
    variant = client.normalize_hgvs(hgvs, assembly, case_id=case_id)
    if variant.warnings:
        variant.validated_hgvs = [hgvs]
        variant.warnings.append("HGVS retained without external validation")
    return variant
