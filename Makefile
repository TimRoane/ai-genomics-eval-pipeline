.PHONY: setup test demo dashboard regression

setup:
	pip install -e ".[dev]"

test:
	pytest -q

demo:
	genomics-eval run-all \
		--cases data/raw/input_cases.jsonl \
		--clinvar data/raw/clinvar_subset.vcf \
		--db data/results/eval.sqlite \
		--run-name local-demo

dashboard:
	streamlit run src/genomics_eval/dashboard/app.py

regression:
	genomics-eval regression \
		--current data/results/scores.parquet \
		--baseline data/baselines/scores_v1.parquet \
		--thresholds configs/thresholds.yaml \
		--out data/results/regression_report.json
