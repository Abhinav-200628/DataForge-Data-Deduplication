# Production-Minded Data Deduplication Pipeline

A robust, enterprise-grade Master Data Management (MDM) deduplication and entity resolution pipeline for **Customer** and **Product** records built with Python 3.11+, pandas, RapidFuzz, and SQLite.

---

## Key Features

1. **Explicit Entity Schemas & Cross-Entity Safety**: Strict data models for Customers and Products prevent cross-entity contamination.
2. **Multi-Tiered Entity Resolution**:
   - `EXACT_MATCH`: Automated deterministic links (Tax ID, UPC, SKU + Brand, Email + Surname).
   - `PROBABLE_MATCH`: Corroborated multi-attribute matches (RapidFuzz Name + Exact Phone/Address/Price).
   - `MANUAL_REVIEW`: Borderline or conflicting cases (e.g. shared family emails, price divergence).
   - `DISTINCT`: Unmatched records established as new golden masters.
3. **Hard-Conflict Safeguards & Transitive Safety**:
   - Merging is strictly vetoed if records have conflicting non-null Tax IDs, birthdates, UPCs, or brands.
   - Detects and partitions unsafe transitive clusters (e.g. if A matches B, and B matches C, but A and C conflict).
   - **Shared Contact Guard**: Prevents merging family members or roommates who share an email or phone number.
4. **Deterministic Field-Level Survivorship**:
   - Field values consolidate using configurable source priority (`ERP > CRM > WEB`), recency timestamps, completeness, and stable tie-breakers.
   - Generates stable, immutable Master IDs using `UUIDv5`.
   - Contact channels are preserved as primary vs. secondary alias arrays (`secondary_emails`, `secondary_phones`).
5. **Rerun Idempotency**:
   - Processing the exact same dataset repeatedly updates existing records in-place without creating duplicate master records or duplicate lineage entries.
6. **Data Quality & Quarantine Store**:
   - Isolates invalid, malformed, or duplicate source-key records with explicit rejection reasons while preserving source identity.
7. **Mathematical Reconciliation Enforcement**:
   - Asserts strict conservation laws:
     $$\text{Total Input Records} = \text{Valid Processed} + \text{Quarantined}$$
8. **Synthetic Scale Generator & Benchmark**:
   - Configurable generator produces up to 100,000+ records with isolated ground-truth labels for precision/recall evaluations.

---

## Folder Structure

```text
data-deduplication-pipeline/
├── data/
│   ├── sample/                   # Sample datasets and isolated ground truth
│   └── synthetic/                # Large generated scale datasets
├── docs/
│   ├── architecture.md           # Architecture, transitive merge protection, and design diagrams
│   └── data_dictionary.md        # Schemas, field constraints, and rejection taxonomy
├── src/
│   └── deduplication/
│       ├── cli.py                # Command-line interface (argparse subcommands)
│       ├── orchestration.py      # Pipeline lifecycle coordinator & reconciliation
│       ├── schemas/              # Dataclass schemas for Customer, Product, Quarantine
│       ├── ingestion/            # Resilient CSV loader with error trapping & schema drift checks
│       ├── normalization/        # Field cleaners (phone, email, address, SKU, UPC)
│       ├── matching/             # RapidFuzz similarity, blocking keys, hard-conflict filters
│       ├── survivorship/         # Deterministic field resolution & UUIDv5 master IDs
│       ├── storage/              # SQLite persistence, WAL mode, atomic upserts, and file exports
│       ├── lineage/              # Source-to-master audit trail and manual review queue
│       ├── generator/            # Deterministic synthetic data generator
│       └── reporting/            # Validation, reconciliation, and ground-truth evaluation
├── tests/
│   ├── unit/                     # Focused unit tests (schemas, normalizers, matchers, survivorship)
│   ├── integration/              # E2E pipeline execution and rerun idempotency tests
│   └── performance/              # Reconciliation balance and ground-truth precision/recall
├── pyproject.toml                # Project packaging configuration
└── README.md                     # Documentation and setup instructions
```

---

## Setup & Installation

### Prerequisites
- Python 3.11 or Python 3.12
- SQLite 3 (bundled with Python)

### 1. Create and Activate Virtual Environment
```bash
python -m venv .venv

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1

# On Linux/macOS:
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
# Or install directly:
pip install pandas rapidfuzz pytest
```

### 3. Link Project Package
```bash
# Add source directory to python path or editable install
pip install -e .
```

---

## CLI Usage Guide

The pipeline provides 5 subcommands via `python -m deduplication.cli`:

### 1. Generate Synthetic Data
Generates realistic customer or product datasets with known duplicate groups, variations, and isolated ground-truth labels:
```bash
python -m deduplication.cli generate-data \
    --entity customer \
    --count 1000 \
    --seed 42 \
    --output-dir data/sample
```

### 2. Run the Deduplication Pipeline
Executes the full deduplication lifecycle on an input CSV:
```bash
python -m deduplication.cli run \
    --entity customer \
    --input data/sample/customers_1000.csv \
    --db pipeline.db \
    --output-dir output
```

### 3. Check Rerun Idempotency
Rerunning the exact same file against the same database produces identical results with zero duplicate rows:
```bash
python -m deduplication.cli run \
    --entity customer \
    --input data/sample/customers_1000.csv \
    --db pipeline.db
```

### 4. Generate Validation & Reconciliation Report
Produces a complete Markdown or JSON report verifying data quality, reconciliation balance, and ground-truth accuracy:
```bash
python -m deduplication.cli report \
    --run-id <RUN_ID> \
    --db pipeline.db \
    --ground-truth data/sample/customers_1000_ground_truth.json \
    --format markdown
```

### 5. Inspect the Manual Review Queue
Lists borderline or ambiguous candidate records flagged for human review:
```bash
python -m deduplication.cli review \
    --db pipeline.db \
    --list \
    --limit 10
```

### 6. Run Scale Performance Benchmark
Runs a performance and throughput test on a large dataset:
```bash
python -m deduplication.cli benchmark \
    --entity customer \
    --count 10000 \
    --db benchmark.db \
    --output-dir benchmark_output
```

---

## Automated Test Suite

Run the full automated test suite with `pytest`:
```bash
pytest -v
```

All 51 automated tests cover:
- Schema validation and boundary checks
- Missing required header columns and schema drift
- Malformed rows and duplicate source keys within a batch
- Phone, email, address, SKU, and UPC check digit normalizers
- Exact matching, corroborated probable matching, and borderline review cases
- Hard-conflict vetoes (Tax ID, DOB, UPC, Brand)
- Shared contact guard (family members sharing email/phone)
- Unsafe transitive merge prevention (cluster conflict partitioning)
- Deterministic survivorship, source priority, recency, and tie-breakers
- Stable Master ID reproducibility
- Rerun idempotency (zero duplicate master records and zero duplicate lineage rows)
- End-to-end customer and product pipelines
- Cross-entity schema isolation
- Mathematical reconciliation conservation assertions

---

## Senior Engineering Design & Trade-Off Notes

### 1. Precision over Recall (Conservative Merging)
- In Master Data Management, **false merges** (incorrectly combining two different people into one identity) cause catastrophic business consequences: privacy breaches, merged credit histories, and regulatory fines under GDPR/CCPA.
- Conversely, **false splits** (treating duplicates as two separate people) only cause minor operational friction.
- **Design Decision**: The pipeline adopts conservative matching thresholds. Any ambiguous case or conflicting identifier is diverted to `MANUAL_REVIEW`, never merged automatically.

### 2. Multi-Pass Blocking vs. $O(N^2)$ Pairwise Comparisons
- Naive pairwise comparisons scale quadratically ($N \times (N-1) / 2$). At 100,000 records, this requires 5 billion comparisons.
- **Design Decision**: We implement multi-pass phonetic and structural blocking keys (Soundex of surname + zip prefix, phone suffix, email domain + initial). Records are only compared if they share a candidate block, reducing candidate pairs by $> 99.7\%$ and enabling 100,000-record execution locally in seconds.

### 3. Transitive Merge Conflict Partitioning
- If Record A matches Record B, and Record B matches Record C, standard graph connected-components would merge $\{A, B, C\}$.
- However, if Record A and Record C have conflicting Tax IDs, this is a transitive false merge.
- **Design Decision**: Before consolidating a cluster, the pipeline performs an exhaustive internal conflict audit. If a hard conflict exists anywhere inside the cluster, the merge is vetoed, conflicting edges are severed, and ambiguous records are routed to manual review.

### 4. Ground-Truth Isolation
- Synthetic data generation stores expected duplicate clusters in a separate JSON file (`customers_ground_truth.json`).
- The input CSV contains **no answer labels or cheat columns**, ensuring pipeline evaluation reflects true real-world data engineering conditions.

---

## Known Limitations & Production Enhancements

1. **Single-Node SQLite Storage**: While SQLite with WAL mode easily handles hundreds of thousands of records on a single node, multi-million record enterprise workloads should migrate to PostgreSQL, Snowflake, or Databricks Delta Lake.
2. **Distributed Blocking with Apache Spark**: For billion-record scale, the blocking and similarity stages can be distributed across worker nodes using PySpark or DuckDB.
3. **Active Learning / Human-in-the-Loop Feedback**: A web interface (e.g. Streamlit or React) could allow data stewards to resolve items in `manual_review_queue`, feeding steward decisions back into the model to refine matching thresholds.
