-- Operational Run Audit
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    status TEXT NOT NULL,
    input_count INTEGER DEFAULT 0,
    valid_count INTEGER DEFAULT 0,
    quarantined_count INTEGER DEFAULT 0,
    exact_match_count INTEGER DEFAULT 0,
    probable_match_count INTEGER DEFAULT 0,
    review_count INTEGER DEFAULT 0,
    distinct_count INTEGER DEFAULT 0,
    elapsed_seconds REAL,
    error_summary TEXT
);

-- Quarantined Records (Data Quality Failures)
CREATE TABLE IF NOT EXISTS quarantine_records (
    quarantine_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    source_system TEXT NOT NULL,
    source_record_id TEXT NOT NULL,
    raw_payload TEXT NOT NULL,
    rejection_reasons TEXT NOT NULL,
    quarantined_at TEXT NOT NULL,
    UNIQUE(entity_type, source_system, source_record_id)
);

-- Master Customer Golden Records
CREATE TABLE IF NOT EXISTS master_customers (
    master_id TEXT PRIMARY KEY,
    first_name TEXT,
    last_name TEXT NOT NULL,
    primary_email TEXT,
    secondary_emails TEXT,
    primary_phone TEXT,
    secondary_phones TEXT,
    street_address TEXT,
    city TEXT,
    state TEXT,
    postal_code TEXT,
    country TEXT,
    tax_id TEXT,
    date_of_birth TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    record_version INTEGER DEFAULT 1
);

-- Master Product Golden Records
CREATE TABLE IF NOT EXISTS master_products (
    master_id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    brand TEXT NOT NULL,
    primary_sku TEXT,
    secondary_skus TEXT,
    primary_upc_ean TEXT,
    category TEXT,
    unit_price REAL,
    currency TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    record_version INTEGER DEFAULT 1
);

-- Provenance & Lineage (Source -> Master)
CREATE TABLE IF NOT EXISTS record_lineage (
    lineage_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    source_system TEXT NOT NULL,
    source_record_id TEXT NOT NULL,
    master_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    match_rule_id TEXT NOT NULL,
    confidence_score REAL NOT NULL,
    merge_reasons TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(entity_type, source_system, source_record_id)
);

-- Manual Review Queue
CREATE TABLE IF NOT EXISTS manual_review_queue (
    review_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    source_system TEXT NOT NULL,
    source_record_id TEXT NOT NULL,
    candidate_master_id TEXT,
    similarity_score REAL,
    reasons TEXT NOT NULL,
    status TEXT DEFAULT 'PENDING',
    created_at TEXT NOT NULL,
    UNIQUE(entity_type, source_system, source_record_id, run_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_lineage_master ON record_lineage(master_id);
CREATE INDEX IF NOT EXISTS idx_lineage_run ON record_lineage(run_id);
CREATE INDEX IF NOT EXISTS idx_quarantine_run ON quarantine_records(run_id);
CREATE INDEX IF NOT EXISTS idx_review_run ON manual_review_queue(run_id);

