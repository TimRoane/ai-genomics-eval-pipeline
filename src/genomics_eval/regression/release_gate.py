from __future__ import annotations

from genomics_eval.schemas import RegressionReport


def release_gate(report: RegressionReport) -> int:
    return 0 if report.passed else 1
