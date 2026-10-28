# Architecture & Design Specification: Enterprise Data Deduplication Pipeline

## 1. High-Level Architecture

The Data Deduplication Pipeline implements an enterprise-grade Master Data Management (MDM) framework following an **Ingest -> Validate -> Standardize -> Block -> Match -> Consolidate -> Audit** workflow.

```
+-------------------------------------------------------------------------------+
|                             INPUT DATA SOURCES                                |
|  - Customer CSVs (CRM, ERP, Billing, Web)                                     |
|  - Product Catalogs (SAP, PIM, Shopify, Amazon)                               |
+---------------------------------------+---------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
|                       INGESTION & DATA QUALITY GATE                           |
|  - Schema Validation (Required header check & unexpected drift detection)     |
|  - Row-Level Typing & Range Audits (Dates, emails, non-negative prices)       |
|  - Batch-Level Duplicate Source Key Prevention                                |
+-------------------+-----------------------------------+-----------------------+
                    |                                   |
         (Failed Validation)                     (Passed Validation)
                    v                                   v
+------------------------------------+   +--------------------------------------+
|          QUARANTINE STORE          |   |      CLEANSING & NORMALIZATION       |
| - Preserves full source identity   |   | - Lowercase emails, stripped tokens  |
| - Records explicit rejection codes |   | - E.164 phone numbers (digits only)  |
| - Retains raw payload JSON         |   | - Street suffix abbreviations        |
+------------------------------------+   | - GTIN/UPC modulo-10 check digits    |
                                         +------------------+-------------------+
                                                            |
                                                            v
+-------------------------------------------------------------------------------+
|                       MULTI-PASS BLOCKING (Candidate Indexing)                |
|  - Prevents O(N^2) comparison explosions at 100k+ record scale                |
|  - Customer Passes: Soundex(Surname)+Zip, Phone Suffix, Domain+Initial, TaxID |
|  - Product Passes: Brand+Category, UPC Prefix, SKU Prefix                     |
+---------------------------------------+---------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
|                       MULTI-TIERED ENTITY RESOLUTION                          |
|  - Hard Conflict Filters (Conflicting Tax IDs, DOBs, UPCs, Brands)            |
|  - Shared Contact Guard (Family/Roommates sharing email/phone -> Review)      |
|  - Tier 1: Deterministic Exact (Tax ID, UPC, SKU+Brand, Email+Surname)        |
|  - Tier 2: Corroborated Probable (RapidFuzz Name + Exact Phone/Address/Price) |
|  - Tier 3: Manual Review Queue (Borderline scores, ambiguous corroboration)   |
|  - Tier 4: Distinct (No links)                                                |
+---------------------------------------+---------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
|                     SAFE TRANSITIVE CLUSTER RESOLUTION                        |
|  - Connected components graph resolution                                      |
|  - Pairwise cluster conflict verification                                     |
|  - Vetoes unsafe transitive merges (e.g. A=B and B=C where A and C conflict)  |
+---------------------------------------+---------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
|                     DETERMINISTIC SURVIVORSHIP ENGINE                         |
|  - Source Priority Weighting (ERP > CRM > WEB)                                |
|  - Recency Policy (Latest updated_at timestamp)                               |
|  - Completeness First (Non-null valid value beats null)                       |
|  - Deterministic Tie-Breaker (Alphabetical source_record_id)                  |
|  - Secondary Collection (Maintains lists of secondary emails, phones, SKUs)   |
|  - Deterministic Master ID: UUIDv5(Namespace, Entity:AnchorSystem:AnchorID)   |
+---------------------------------------+---------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
|                     PERSISTENCE & RECONCILIATION GATE                         |
|  - Transactional SQLite Publishing (Atomic Commit)                            |
|  - Idempotent Upserts (UNIQUE constraints on source_system + source_record_id)|
|  - Mathematical Conservation Check (In == Valid + Quarantine)                 |
|  - CSV and JSON Export Engine                                                 |
+-------------------------------------------------------------------------------+
```

---

## 2. Unsafe Transitive Merge Protection

A major risk in naive entity resolution is **transitive false merging**.

### The Problem Scenario:
1. Record A: `John Smith`, Tax ID `111-11-1111`, Email: `family@home.com`
2. Record B: `John Smith`, Tax ID `None`,        Email: `family@home.com`
3. Record C: `John Smith`, Tax ID `222-22-2222`, Email: `family@home.com`

- Pair `(A, B)` matches on exact email and name.
- Pair `(B, C)` matches on exact email and name.
- In a naive graph or disjoint-set algorithm, $A \sim B$ and $B \sim C$ leads to merging $\{A, B, C\}$.
- **The Catastrophe:** Record A and Record C have **conflicting Tax IDs** (they are two distinct individuals who happen to share an email, such as father and son or fraud). Merging them into a single Master identity would corrupt credit and legal records.

### Our Solution (`clustering.py`):
Before consolidating any candidate cluster with size $\ge 2$:
1. An exhaustive internal conflict audit is conducted across all pairs in the candidate cluster.
2. If any two records in the cluster have hard conflicts (differing Tax IDs, differing birthdates, differing UPCs, or differing brands), the merge is **vetoed**.
3. The cluster is severed, the conflicting pair is routed to `manual_review_queue`, and all records in the cluster are published as distinct records until human data stewards resolve the ambiguity.

---

## 3. Candidate Blocking vs. $O(N^2)$ Pairwise Comparisons

Comparing $N$ records pairwise requires:
$$\frac{N \times (N - 1)}{2} \text{ comparisons}$$

- For $N = 1,000$: $499,500$ comparisons (~0.5 seconds).
- For $N = 100,000$: $4,999,950,000$ comparisons (~several hours or out-of-memory crash).

### Multi-Pass Blocking Strategy:
Instead of comparing every row to every row, records are partitioned into **blocks** based on phonetic and structural attributes:
- **Customer Blocking:**
  1. `Soundex(last_name) + "_" + postal_code[:3]`
  2. Last 7 digits of phone number
  3. Email domain + first letter of last name
  4. Normalized Tax ID
- **Product Blocking:**
  1. `Brand + "_" + Category`
  2. First 6 digits of UPC/EAN
  3. First 4 characters of SKU

Records are only compared if they share at least one blocking key. This reduces candidate comparisons by **$> 99.7\%$**, enabling the pipeline to process 100,000 records smoothly on a local machine.

---

## 4. Deterministic Field-Level Survivorship Matrix

When multiple source records are linked to one master entity, scalar and collection fields are consolidated using a 4-tier decision hierarchy:

| Hierarchy Tier | Rule | Description |
| :--- | :--- | :--- |
| **Tier 1: Completeness** | Non-null beats null | An empty, blank, or null field can never overwrite a valid value. |
| **Tier 2: Source Priority** | System weight | Source systems have explicit trust weights: `ERP (100) > CRM (80) > WEB (60) > MARKETING (40)`. |
| **Tier 3: Recency** | Latest `updated_at` | If two systems have equal priority, the record with the most recent valid timestamp wins. |
| **Tier 4: Tie-Breaker** | Lexicographical ID | If priority and timestamp are identical, sort alphabetically by `source_record_id`. |

### Contact Channel Aggregation:
- The winning record provides the `primary_email` or `primary_phone`.
- All other distinct, valid contact channels are preserved in `secondary_emails` and `secondary_phones` JSON arrays in the master table and lineage records.

---

## 5. Rerun Idempotency Guarantees

In modern data pipelines, a job may be re-triggered due to network pauses, schedule retries, or downstream failures. A production pipeline must be **idempotent**: running the same data twice must leave the database in the exact same state as running it once.

### How We Guarantee Idempotency:
1. **Deterministic Master IDs**: Generated using `UUIDv5` seeded with `(entity_type, anchor_system, anchor_record_id)`. The ID is purely a function of the canonical record identity, independent of row processing order.
2. **Database Unique Constraints**:
   - `record_lineage` enforces `UNIQUE(entity_type, source_system, source_record_id)`.
   - `master_*` tables use `PRIMARY KEY (master_id)`.
   - `quarantine_records` enforces `UNIQUE(entity_type, source_system, source_record_id)`.
3. **Atomic Upserts**: SQLite `INSERT ... ON CONFLICT DO UPDATE` ensures existing records are refreshed in-place rather than generating duplicate rows.

