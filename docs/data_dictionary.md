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
