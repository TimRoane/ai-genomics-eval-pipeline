from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional

import pandas as pd
import typer
import yaml
from rich.console import Console

from genomics_eval.ai.model_client import MockModelClient, OfflineModelClient
from genomics_eval.ai.prompt_builder import build_prompt
from genomics_eval.annotation.clinvar import ClinVarAnnotator
from genomics_eval.annotation.dbsnp import DbSnpAnnotator
from genomics_eval.database.db import write_ai_outputs, write_run_metadata, write_scores
from genomics_eval.io import read_json, read_jsonl, write_json, write_jsonl, write_parquet
from genomics_eval.normalization.hgvs_normalizer import normalize_hgvs
from genomics_eval.normalization.vcf_normalizer import normalize_vcf_record, split_multiallelic_alt
from genomics_eval.regression.compare_runs import compare_to_baseline
from genomics_eval.regression.release_gate import release_gate
from genomics_eval.schemas import AIOutput, EvalScore, InputCase, NormalizedVariant, RegressionReport, VariantAnnotation
from genomics_eval.scoring.aggregate import aggregate_scores
from genomics_eval.scoring.field_scorers import score_case

app = typer.Typer(help="Evaluate AI-generated genomic variant interpretations.")
console = Console()


@app.command()
def normalize(
    cases: Path = typer.Option(..., help="Input JSONL cases."),
    out: Path = typer.Option(..., help="Output normalized variants parquet."),
) -> None:
    variants = normalize_cases(cases)
    write_parquet(out, variants)
    console.print(f"Wrote {len(variants)} normalized variants to {out}")


@app.command()
def annotate(
    normalized: Path = typer.Option(..., help="Normalized variants parquet."),
    clinvar: Path = typer.Option(..., help="ClinVar subset VCF."),
    dbsnp: Optional[Path] = typer.Option(None, help="dbSNP subset TSV."),
    out: Path = typer.Option(..., help="Output annotations parquet."),
) -> None:
    annotations = annotate_variants(normalized, clinvar, dbsnp)
    write_parquet(out, annotations)
    console.print(f"Wrote {len(annotations)} annotations to {out}")


@app.command("run-ai")
def run_ai(
    dataset: Path = typer.Option(..., help="Evaluation dataset parquet."),
    model: str = typer.Option("mock", help="mock or offline."),
    out: Path = typer.Option(..., help="AI outputs JSONL."),
    offline_outputs: Optional[Path] = typer.Option(None, help="Precomputed output JSONL for offline mode."),
) -> None:
    outputs, _prompts = run_ai_dataset(dataset, model, offline_outputs)
    write_jsonl(out, outputs)
    console.print(f"Wrote {len(outputs)} AI outputs to {out}")


@app.command()
def score(
    cases: Path = typer.Option(..., help="Input JSONL cases."),
    outputs: Path = typer.Option(..., help="AI outputs JSONL."),
    annotations: Path = typer.Option(..., help="Annotations parquet."),
    out: Path = typer.Option(..., help="Scores parquet."),
) -> None:
    scores = score_outputs(cases, outputs, annotations)
    write_parquet(out, scores)
    console.print(f"Wrote {len(scores)} scores to {out}")


@app.command()
def regression(
    current: Path = typer.Option(..., help="Current scores parquet."),
    baseline: Path = typer.Option(..., help="Baseline scores parquet or fallback metrics sibling."),
    thresholds: Path = typer.Option(..., help="Threshold YAML."),
    out: Path = typer.Option(..., help="Regression report JSON."),
) -> None:
    report = build_regression_report(current, baseline, thresholds)
    write_json(out, report.model_dump(mode="json"))
    console.print(f"Release gate: {'PASS' if report.passed else 'FAIL'}")
    raise typer.Exit(release_gate(report))


@app.command("run-all")
def run_all(
    cases: Path = typer.Option(..., help="Input JSONL cases."),
    clinvar: Path = typer.Option(..., help="ClinVar subset VCF."),
    db: Path = typer.Option(Path("data/results/eval.sqlite"), help="SQLite results DB."),
    run_name: str = typer.Option("local-demo", help="Run name."),
) -> None:
    normalized_path = Path("data/processed/normalized_variants.parquet")
    annotations_path = Path("data/processed/annotated_variants.parquet")
    dataset_path = Path("data/processed/eval_dataset.parquet")
    outputs_path = Path("data/results/ai_outputs.jsonl")
    scores_path = Path("data/results/scores.parquet")
    regression_path = Path("data/results/regression_report.json")

    variants = normalize_cases(cases)
    write_parquet(normalized_path, variants)
    annotations = annotate_variants(normalized_path, clinvar, Path("data/reference/dbsnp_subset.tsv"))
    write_parquet(annotations_path, annotations)
    write_eval_dataset(cases, annotations_path, dataset_path)
    outputs, prompts = run_ai_dataset(dataset_path, "mock", None)
    write_jsonl(outputs_path, outputs)
    scores = score_outputs(cases, outputs_path, annotations_path)
    write_parquet(scores_path, scores)
    metrics = aggregate_scores(scores)
    report = compare_to_baseline(metrics, _load_baseline_metrics(Path("data/baselines/scores_v1.parquet")), _load_yaml(Path("configs/thresholds.yaml")))
    write_json(regression_path, report.model_dump(mode="json"))
    _write_summary(Path("data/results/latest_summary.md"), metrics, report)

    run_id = write_run_metadata(db, run_name)
    write_ai_outputs(db, run_id, outputs, prompts)
    write_scores(db, run_id, scores)

    console.print(f"Overall pass rate: {metrics['overall_pass_rate']:.1%}")
    console.print(f"Classification accuracy: {metrics['classification_accuracy']:.1%}")
    console.print(f"Transcript accuracy: {metrics['transcript_accuracy']:.1%}")
    console.print(f"Critical failures: {metrics['critical_failures']}")
    console.print(f"Release gate: {'PASS' if report.passed else 'FAIL'}")


@app.command()
def dashboard(
    scores: Path = typer.Option(Path("data/results/scores.parquet"), help="Scores parquet."),
    regression: Path = typer.Option(Path("data/results/regression_report.json"), help="Regression report JSON."),
    outputs: Path = typer.Option(Path("data/results/ai_outputs.jsonl"), help="AI outputs JSONL."),
    cases: Path = typer.Option(Path("data/raw/input_cases.jsonl"), help="Input cases JSONL."),
    annotations: Path = typer.Option(Path("data/processed/annotated_variants.parquet"), help="Annotations parquet."),
) -> None:
    subprocess.run(
        [
            "streamlit",
            "run",
            "src/genomics_eval/dashboard/app.py",
            "--",
            str(scores),
            str(regression),
            str(outputs),
            str(cases),
            str(annotations),
        ],
        check=False,
    )


def normalize_cases(cases_path: Path) -> list[NormalizedVariant]:
    variants: list[NormalizedVariant] = []
    for row in read_jsonl(cases_path):
        case = InputCase.model_validate(row)
        if case.input_type == "VCF_RECORD":
            for allele in split_multiallelic_alt(
                {"chrom": case.chrom, "pos": case.pos, "ref": case.ref, "alt": case.alt}
            ):
                variants.append(
                    normalize_vcf_record(
                        allele.chrom,
                        allele.pos,
                        allele.ref,
                        allele.alt,
                        case.assembly,
                        case_id=case.case_id,
                    )
                )
        elif case.input_type == "HGVS" and case.input_variant:
            variant = normalize_hgvs(case.input_variant, case.assembly, case_id=case.case_id)
            variant.gene_symbol = case.expected_gene
            variant.selected_transcript = variant.selected_transcript or case.expected_transcript
            variants.append(variant)
        else:
            variants.append(NormalizedVariant(case_id=case.case_id, assembly=case.assembly, warnings=["Unsupported input type"]))
    return variants


def annotate_variants(normalized_path: Path, clinvar_path: Path, dbsnp_path: Path | None) -> list[VariantAnnotation]:
    normalized_df = pd.read_parquet(normalized_path)
    clinvar = ClinVarAnnotator(clinvar_path)
    dbsnp = DbSnpAnnotator(dbsnp_path) if dbsnp_path and dbsnp_path.exists() else None
    annotations: list[VariantAnnotation] = []
    for row in _clean_records(normalized_df):
        variant = NormalizedVariant.model_validate(row)
        annotation = clinvar.annotate(variant)
        if dbsnp:
            rsid = dbsnp.annotate(variant)
            if rsid:
                annotation.dbsnp_id = rsid
        annotations.append(annotation)
    return annotations


def write_eval_dataset(cases_path: Path, annotations_path: Path, out: Path) -> None:
    cases = {row["case_id"]: row for row in read_jsonl(cases_path)}
    annotations = {row["case_id"]: row for row in pd.read_parquet(annotations_path).to_dict("records")}
    rows = []
    for case_id, case in cases.items():
        row = InputCase.model_validate(case).model_dump(mode="json")
        for key, value in annotations.get(case_id, {}).items():
            row[f"annotation_{key}"] = value
        rows.append(row)
    write_parquet(out, rows)


def run_ai_dataset(dataset_path: Path, model: str, offline_outputs: Path | None) -> tuple[list[AIOutput], dict[str, str]]:
    df = pd.read_parquet(dataset_path)
    client = OfflineModelClient(offline_outputs) if model == "offline" and offline_outputs else MockModelClient()
    outputs: list[AIOutput] = []
    prompts: dict[str, str] = {}
    for row in _clean_records(df):
        if row.get("metadata") is None:
            row["metadata"] = {}
        case = InputCase.model_validate(row)
        annotation = _annotation_from_dataset_row(row)
        prompt = build_prompt(case, annotation)
        prompts[case.case_id] = prompt
        outputs.append(client.generate(case, prompt, annotation))
    return outputs, prompts


def score_outputs(cases_path: Path, outputs_path: Path, annotations_path: Path) -> list[EvalScore]:
    cases = {row["case_id"]: InputCase.model_validate(row) for row in read_jsonl(cases_path)}
    outputs = {row["case_id"]: AIOutput.model_validate(row) for row in read_jsonl(outputs_path)}
    annotation_rows = _clean_records(pd.read_parquet(annotations_path))
    annotations = {row["case_id"]: VariantAnnotation.model_validate(row) for row in annotation_rows}
    return [
        score_case(case, annotations.get(case_id), outputs.get(case_id) or AIOutput(case_id=case_id, model_name="missing", prompt_version="v1", response_text=""))
        for case_id, case in cases.items()
    ]


def build_regression_report(current_path: Path, baseline_path: Path, thresholds_path: Path) -> RegressionReport:
    current_scores = [EvalScore.model_validate(row) for row in _clean_records(pd.read_parquet(current_path))]
    current_metrics = aggregate_scores(current_scores)
    baseline_metrics = _load_baseline_metrics(baseline_path)
    return compare_to_baseline(current_metrics, baseline_metrics, _load_yaml(thresholds_path))


def _clean_records(df: pd.DataFrame) -> list[dict]:
    records: list[dict] = []
    for row in df.to_dict("records"):
        records.append({key: _none_if_missing(value) for key, value in row.items()})
    return records


def _none_if_missing(value):
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        return value
    return value


def _annotation_from_dataset_row(row: dict) -> VariantAnnotation:
    payload = {
        key.removeprefix("annotation_"): value
        for key, value in row.items()
        if key.startswith("annotation_")
    }
    return VariantAnnotation.model_validate(payload) if payload else VariantAnnotation(case_id=row["case_id"])


def _load_baseline_metrics(path: Path) -> dict | None:
    if path.exists():
        scores = [EvalScore.model_validate(row) for row in _clean_records(pd.read_parquet(path))]
        return aggregate_scores(scores)
    fallback = path.with_name("metrics_v1.json")
    if fallback.exists():
        return read_json(fallback)
    return None


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write_summary(path: Path, metrics: dict, report: RegressionReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# Latest Evaluation Summary",
                "",
                f"Overall pass rate: {metrics['overall_pass_rate']:.1%}",
                f"Classification accuracy: {metrics['classification_accuracy']:.1%}",
                f"Transcript accuracy: {metrics['transcript_accuracy']:.1%}",
                f"Critical failures: {metrics['critical_failures']}",
                f"Release gate: {'PASS' if report.passed else 'FAIL'}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    app()
