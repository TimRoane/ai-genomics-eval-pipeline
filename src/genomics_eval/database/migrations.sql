CREATE TABLE IF NOT EXISTS eval_runs (
    run_id TEXT PRIMARY KEY,
    run_name TEXT,
    created_at TEXT,
    git_commit TEXT,
    model_name TEXT,
    prompt_version TEXT,
    dataset_version TEXT,
    clinvar_version TEXT
);

CREATE TABLE IF NOT EXISTS eval_scores (
    run_id TEXT,
    case_id TEXT,
    passed BOOLEAN,
    gene_correct BOOLEAN,
    transcript_correct BOOLEAN,
    hgvs_correct BOOLEAN,
    classification_correct BOOLEAN,
    condition_correct BOOLEAN,
    hallucination_detected BOOLEAN,
    severity TEXT,
    failure_modes TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS ai_outputs (
    run_id TEXT,
    case_id TEXT,
    prompt TEXT,
    response_text TEXT,
    parsed_json TEXT
);
