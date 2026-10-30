# AI Transparency & Prompt History Disclosure
*In accordance with YottaFlex AI Recruitment Drive Candidate Project Submission Guidelines (Section 03: Use LLMs Transparently & FAQs 4, 6)*

---

## 1. AI Assistance Overview & Disclosure

In developing the **DataForge Data Deduplication Platform**, AI coding assistants (Google Antigravity / Gemini 2.5) were utilized as collaborative engineering pair-programmers. 

### Where AI Accelerated the Work:
- **Rapid Prototyping & Scaffolding**: Fast generation of boilerplate Pydantic schemas, Python dataclasses, and React/Tailwind component hierarchies.
- **Algorithm Implementations**: Accelerated drafting of phonetic Soundex key generation, Levenshtein/RapidFuzz token-sort similarity wrappers, and GTIN-14 modulo-10 check-digit validators.
- **Exhaustive Test Case Generation**: Generated parametric edge cases in `pytest` for boundary dates, corrupted CSV rows, and schema drift.
- **Synthetic Data Generation**: Generated realistic mock customer and product records with controlled noise, typological variations, and ground-truth duplicate clusters.
- **Frontend Observability Suite**: Accelerated development of the 8-page dark-themed React + Vite web dashboard and interactive Recharts visualizations.

### What Was Personally Reviewed, Changed & Validated:
- **Architectural & Business Invariants**: Enforced conservative merging policies (prioritizing precision over recall to prevent false merges), ensuring no automatic merges occur when hard conflicts exist.
- **Transitive Merge Conflict Auditing**: Personally audited and structured the connected-components clustering engine to guarantee that transitive merges (e.g., $A=B$ and $B=C$ where $A$ and $C$ conflict) are vetoed and routed to manual review.
- **Thread Safety & ACID Persistence**: Added concurrency locks (`threading.Lock`) to the FastAPI pipeline service to prevent SQLite single-file write locking during concurrent UI operations.
- **Zero-Dependency Export Fallback**: Implemented standard library CSV/JSON export fallback routines when optional numerical libraries (NumPy/Pandas) encounter environment-specific C-extension import issues.
- **Mathematical Reconciliation Conservation**: Personally verified and wrote unit tests for the strict conservation law: $\text{Total Input Records} = \text{Valid Processed} + \text{Quarantined}$.
- **Performance & Memory Profiling**: Executed and verified the multi-scale benchmarks (1k, 10k, and 100k records) on local Windows hardware, validating that peak memory stayed under 815 MB.

---

## 2. Comprehensive Prompt History

Below is the chronological record of prompt instructions submitted during the development lifecycle:

### Stage A — Schemas and Ingestion
```text
Implement the schemas and ingestion module. Add tests for valid CSVs, empty input, malformed rows, missing columns, duplicate source keys, and unexpected schema changes. Run the tests and explain the results.
```

### Stage B — Normalization and Matching
```text
Implement customer and product matching as separate configurable strategies. Return match evidence, score, decision, and reason. Prevent unsafe transitive merges and test ambiguous and conflicting cases.
```

### Stage C — Survivorship and Lineage
```text
Implement field-level survivorship, stable master IDs, source-to-master lineage, merge decisions, and a manual-review queue. Ensure tie-breaking is deterministic and preserve all original source records.
```

### Stage D — Publishing and Idempotency
```text
Implement transactional publishing, run history, unique constraints, idempotent reruns, restart handling, and safe output generation. Add tests proving that repeated runs do not create duplicate masters or lineage.
```

### Stage E — Reports and Data Generation
```text
Create a fixed-seed synthetic data generator with known duplicate groups and separately stored expected labels. Add a 100,000-record benchmark, data-quality report, and reconciliation assertions.
```

### End-to-End Pipeline Audit & Edge-Case Verification
```text
Audit the complete data deduplication pipeline against the assessment requirements.
Do not modify code blindly. First inspect the implementation and identify defects or missing requirements.
Then:
1. Run the full pytest suite and report the actual results.
2. Add missing tests for exact matches, probable matches, false-positive safeguards, empty inputs, malformed input, schema changes, missing values, duplicate source keys, late-arriving data, partial failure, retry, and idempotency.
3. Check that master IDs and survivorship results are deterministic across repeated runs.
4. Verify that every accepted source record maps to a master or has a documented exclusion reason.
5. Verify that every rejected record is traceable to its source and has a rejection reason.
6. Verify that review-queue entries contain matching evidence and a clear reason for manual review.
7. Check that the database and exported outputs reconcile with the run report.
8. Test the same input twice and compare the resulting master records, lineage, and counts.
9. Run the synthetic-data generator and benchmark at a small scale first, then at 100,000 records.
10. Measure runtime and, where practical, peak memory. Document the machine, dataset size, elapsed time, and limitations.
11. Fix any defects found and rerun all relevant tests.
12. Produce a final checklist showing PASS or FAIL with actual supporting evidence. Never mark an unexecuted test as passing.
Finally, explain the remaining limitations in beginner-friendly language and list the exact commands required to reproduce the results from a clean environment.
```

### Full-Stack Enterprise Web Frontend & API Integration
```text
Build a Professional Enterprise Frontend for Data Deduplication Pipeline:
- Build an attractive, production-minded frontend with a premium dark theme (#080D18, #0D1423, #111B2D, cyan/emerald accents) named DATAFORGE Data Deduplication Platform.
- Technology stack: React, Vite, TypeScript, Tailwind CSS, Lucide React, Recharts, React Router.
- Build a thin FastAPI service in src/deduplication/api/ that interfaces with the existing SQLite database and pipeline orchestrator.
- 8 views: Overview, Pipeline Runs, Customer Catalog, Product Catalog, Review Queue, Data Quality, Reports, Settings.
- Support real backend execution, live pagination, search filtering, manual review triage with audit notes, and lineage inspection modals.
- Preserve existing CLI commands, schemas, and all existing unit tests.
```

### Operational & Environment Debugging
```text
1. Diagnose discrepancy where NumPy was missing in virtual environment and provide standard-library export fallback.
2. Resolve PowerShell reserved character (<) issue in CLI documentation by enabling auto-detection of latest run ID.
3. Build one-click Windows launcher scripts (start.ps1 and start.bat) to run both backend and frontend simultaneously.
4. Resolve Git authentication mismatch in Windows Credential Manager to push directly under candidate account.
```

