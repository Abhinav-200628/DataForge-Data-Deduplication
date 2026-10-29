# Data Dictionary & Schema Specification

## 1. Customer Schemas

### A. Customer Source Schema (Raw Ingestion)

| Field Name | Type | Required | Description | Validation Rule |
| :--- | :--- | :--- | :--- | :--- |
| `source_system` | `string` | **Yes** | Originating system name (e.g. `CRM`, `ERP`) | Non-empty string |
| `source_record_id` | `string` | **Yes** | Primary key in originating source system | Non-empty string, unique per system |
| `first_name` | `string` | No | Given personal name | Clean text |
| `last_name` | `string` | **Yes** | Surname / family name | Required for entity matching |
| `email` | `string` | No | Customer contact email | Valid RFC email regex format |
| `phone` | `string` | No | Customer telephone number | Digits-only (10-15 digits) |
| `street_address` | `string` | No | Physical street address | Clean text |
| `city` | `string` | No | Municipality / City | Clean text |
| `state` | `string` | No | State or province code | Clean text |
| `postal_code` | `string` | No | Zip or postal code | Standardized 5-digit US zip |
| `country` | `string` | No | Country code (defaults to `US`) | 2-letter uppercase |
| `tax_id` | `string` | No | Social Security Number / National Tax ID | Standard 9-digit format (`XXX-XX-XXXX`) |
| `date_of_birth` | `string` | No | Birthdate (`YYYY-MM-DD`) | Valid date, cannot be in future |
| `updated_at` | `string` | **Yes** | Timestamp of last record update | Valid ISO 8601 timestamp |

### B. Master Customer Schema (`master_customers`)

| Field Name | Type | Description |
| :--- | :--- | :--- |
| `master_id` | `TEXT (PK)` | Deterministic UUIDv5 golden entity identifier |
| `first_name` | `TEXT` | Consolidated first name |
| `last_name` | `TEXT` | Consolidated last name |
| `primary_email` | `TEXT` | Primary email selected by survivorship policy |
| `secondary_emails`| `JSON TEXT` | Array of all distinct valid secondary emails |
| `primary_phone` | `TEXT` | Primary phone selected by survivorship policy |
| `secondary_phones`| `JSON TEXT` | Array of all distinct valid secondary phones |
| `street_address` | `TEXT` | Consolidated street address |
| `city` | `TEXT` | Consolidated city |
| `state` | `TEXT` | Consolidated state |
| `postal_code` | `TEXT` | Consolidated postal code |
| `country` | `TEXT` | 2-letter country code |
| `tax_id` | `TEXT` | Consolidated Tax ID |
| `date_of_birth` | `TEXT` | Consolidated date of birth |
| `created_at` | `TEXT` | ISO 8601 timestamp when master was first created |
| `updated_at` | `TEXT` | Latest update timestamp across contributing sources |
| `record_version`| `INTEGER` | Monotonically increasing revision number |

---

## 2. Product Schemas

### A. Product Source Schema (Raw Ingestion)

| Field Name | Type | Required | Description | Validation Rule |
| :--- | :--- | :--- | :--- | :--- |
| `source_system` | `string` | **Yes** | Catalog source (e.g. `SAP`, `SHOPIFY`) | Non-empty string |
| `source_record_id` | `string` | **Yes** | Unique product identifier in source system | Non-empty string |
| `product_name` | `string` | **Yes** | Product catalog title / description | Minimum 2 characters |
| `brand` | `string` | **Yes** | Manufacturer or brand name | Non-empty string |
| `sku` | `string` | No | Stock Keeping Unit | Alphanumeric string |
| `upc_ean` | `string` | No | Universal Product Code / GTIN | 8, 12, 13, or 14 digits with check digit |
| `category` | `string` | No | Product taxonomy / category | Clean text |
| `unit_price` | `float` | No | Standard retail price | Numeric $\ge 0.00$ |
| `currency` | `string` | No | Currency ISO code (defaults to `USD`) | 3-letter uppercase |
| `updated_at` | `string` | **Yes** | Timestamp of last source update | Valid ISO 8601 timestamp |

### B. Master Product Schema (`master_products`)

| Field Name | Type | Description |
| :--- | :--- | :--- |
| `master_id` | `TEXT (PK)` | Deterministic UUIDv5 golden entity identifier |
| `product_name` | `TEXT` | Consolidated canonical product title |
| `brand` | `TEXT` | Consolidated brand name |
| `primary_sku` | `TEXT` | Primary SKU selected by survivorship policy |
| `secondary_skus` | `JSON TEXT` | Array of all distinct valid secondary SKUs |
| `primary_upc_ean`| `TEXT` | Consolidated UPC/EAN code |
| `category` | `TEXT` | Consolidated product taxonomy |
| `unit_price` | `REAL` | Consolidated unit price |
| `currency` | `TEXT` | 3-letter ISO currency code |
| `created_at` | `TEXT` | Timestamp when master was first created |
| `updated_at` | `TEXT` | Latest update timestamp |
| `record_version`| `INTEGER` | Monotonically increasing revision number |

---

## 3. Quarantine & Audit Rejection Taxonomy

When records fail data-quality checks, they are routed to `quarantine_records` with one of the following explicit error codes:

| Rejection Code | Description | Example Cause |
| :--- | :--- | :--- |
| `MISSING_REQUIRED_FIELD` | Mandatory schema column is empty or missing | Empty `last_name` or blank `brand` |
| `INVALID_DATA_TYPE` | Field value cannot be converted to expected type | `"FREE"` passed in `unit_price`, or invalid email format |
| `MALFORMED_ROW` | Row contains too few or too many delimiters | CSV line with 7 values when header has 5 |
| `DUPLICATE_SOURCE_KEY` | Same `(source_system, source_record_id)` seen twice in same batch | Duplicate row in input CSV |
| `SCHEMA_MISMATCH` | Mandatory column missing from header or unexpected columns | CSV header missing `updated_at` |
| `EMPTY_INPUT` | File has 0 bytes or no content | Blank file |
| `MALFORMED_DATE` | Date or timestamp cannot be parsed as ISO 8601 | `"2026/99/99"` or future date of birth |
| `MALFORMED_NUMERIC` | Numeric value violates range constraints | Negative `unit_price` (`-19.99`) |

---

## 4. Operational, Lineage, and Review Tables

### A. Record Lineage Schema (`record_lineage`)
Maps every processed valid source record to its resolved golden master identity.

| Field Name | Type | Key | Description |
| :--- | :--- | :--- | :--- |
| `lineage_id` | `TEXT` | PK | Deterministic UUID linking source record to run |
| `entity_type` | `TEXT` | - | Domain entity: `CUSTOMER` or `PRODUCT` |
| `source_system` | `TEXT` | Composite Unique | Originating upstream system (e.g. `CRM`, `ERP`) |
| `source_record_id` | `TEXT` | Composite Unique | Upstream record identifier |
| `master_id` | `TEXT` | FK | Foreign key to `master_customers` or `master_products` |
| `match_decision` | `TEXT` | - | Resolution outcome: `EXACT_MATCH`, `PROBABLE_MATCH`, or `DISTINCT` |
| `match_rule_id` | `TEXT` | - | Rule ID that triggered the merge (e.g. `RULE_CUST_EXACT_TAX_ID`) |
| `similarity_score` | `REAL` | - | Normalized confidence score ($0.00$ to $1.00$) |
| `run_id` | `TEXT` | FK | Pipeline run identifier that processed this row |
| `created_at` | `TEXT` | - | ISO 8601 audit timestamp |

### B. Manual Review Queue Schema (`manual_review_queue`)
Holds ambiguous candidate pairs or conflict-vetoed merges for human data steward triage.

| Field Name | Type | Key | Description |
| :--- | :--- | :--- | :--- |
| `review_id` | `TEXT` | PK | Unique identifier for review ticket |
| `entity_type` | `TEXT` | - | Domain entity: `CUSTOMER` or `PRODUCT` |
| `source_system` | `TEXT` | - | Candidate source system |
| `source_record_id` | `TEXT` | - | Candidate source record identifier |
| `target_master_id` | `TEXT` | - | Potential master entity or competing candidate ID |
| `similarity_score` | `REAL` | - | Similarity score that triggered borderline review |
| `reasons` | `JSON TEXT` | - | Array of reasons (e.g. `SHARED_CONTACT_FLAG`, `PRICE_DIVERGENCE`) |
| `evidence` | `JSON TEXT` | - | Field comparison diff between candidate records |
| `status` | `TEXT` | - | Triage status: `PENDING`, `APPROVED`, or `REJECTED` |
| `run_id` | `TEXT` | FK | Run ID that generated the review item |
| `created_at` | `TEXT` | - | ISO 8601 creation timestamp |
| `updated_at` | `TEXT` | - | ISO 8601 timestamp of steward triage decision |

### C. Pipeline Runs Schema (`pipeline_runs`)
Maintains an immutable historical record of all pipeline execution runs and operational metrics.

| Field Name | Type | Key | Description |
| :--- | :--- | :--- | :--- |
| `run_id` | `TEXT` | PK | Unique run identifier (e.g. `RUN-b2da11738029`) |
| `entity_type` | `TEXT` | - | `CUSTOMER` or `PRODUCT` |
| `started_at` | `TEXT` | - | ISO 8601 pipeline execution start timestamp |
| `ended_at` | `TEXT` | - | ISO 8601 pipeline execution completion timestamp |
| `status` | `TEXT` | - | Status: `COMPLETED`, `FAILED`, or `RUNNING` |
| `input_count` | `INTEGER` | - | Total raw input records in batch |
| `valid_count` | `INTEGER` | - | Count of records passing schema and DQ validation |
| `quarantined_count`| `INTEGER` | - | Count of rejected records routed to quarantine |
| `exact_match_count`| `INTEGER` | - | Records merged via deterministic exact rules |
| `probable_match_count`| `INTEGER`| - | Records merged via corroborated fuzzy similarity |
| `review_count` | `INTEGER` | - | Records routed to `manual_review_queue` |
| `distinct_count` | `INTEGER` | - | New master records created |
| `elapsed_seconds` | `REAL` | - | Total runtime in seconds |
| `error_summary` | `TEXT` | - | Exception stack trace or error summary if failed |


