from __future__ import annotations

from pathlib import Path

import pandas as pd

from genomics_eval.normalization.variant_key import canonical_variant_key
from genomics_eval.schemas import NormalizedVariant


class DbSnpAnnotator:
    def __init__(self, path: str | Path | None = None) -> None:
        self.index: dict[str, str] = {}
        if path:
            self.load_tsv(path)

    def load_tsv(self, path: str | Path) -> None:
        df = pd.read_csv(path, sep="\t")
        self.index = {
            canonical_variant_key(row.assembly, row.chrom, int(row.pos), row.ref, row.alt): row.rsid
            for row in df.itertuples(index=False)
        }

    def annotate(self, variant: NormalizedVariant) -> str | None:
        if not variant.normalized_key:
            return None
        return self.index.get(variant.normalized_key)
