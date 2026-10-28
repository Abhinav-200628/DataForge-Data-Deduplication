"""
Ingestion module for resilient, schema-aware CSV loading.

This module validates file-level integrity, checks headers against known contracts,
processes row-by-row data with error trapping, catches duplicate source keys,
and routes invalid rows to quarantine without crashing the entire batch.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from typing import Any, Optional, Union
import uuid

from deduplication.schemas.common import (
    EntityType,
    RejectionCode,
    ValidationErrorDetail,
)
from deduplication.schemas.customer import CustomerSourceRecord
from deduplication.schemas.product import ProductSourceRecord
from deduplication.schemas.quarantine import QuarantineRecord


class IngestionError(Exception):
    """Base exception for all ingestion-related failures."""


class EmptyInputError(IngestionError):
    """Raised when an input file is 0 bytes or contains no header."""


class SchemaMismatchError(IngestionError):
    """Raised when an input file header is missing mandatory columns or has unexpected schema drift."""


class IngestionIOError(IngestionError):
    """Raised when an input file cannot be found or read."""


# Required columns that must be present in the CSV header
CUSTOMER_REQUIRED_HEADER_COLS: set[str] = {
    "source_system",
    "source_record_id",
    "last_name",
    "updated_at",
}

PRODUCT_REQUIRED_HEADER_COLS: set[str] = {
    "source_system",
    "source_record_id",
    "product_name",
    "brand",
    "updated_at",
}

CUSTOMER_KNOWN_COLS: set[str] = {
    "source_system",
    "source_record_id",
    "first_name",
    "last_name",
    "email",
    "phone",
    "street_address",
    "city",
    "state",
    "postal_code",
    "country",
    "tax_id",
    "date_of_birth",
    "updated_at",
}

PRODUCT_KNOWN_COLS: set[str] = {
    "source_system",
    "source_record_id",
    "product_name",
    "brand",
    "sku",
    "upc_ean",
    "category",
    "unit_price",
    "currency",
    "updated_at",
}


@dataclass
class IngestionResult:
    """Summary of records successfully ingested versus quarantined."""
    entity_type: EntityType
    run_id: str
    file_path: Path
    valid_records: list[Union[CustomerSourceRecord, ProductSourceRecord]] = field(
        default_factory=list
    )
    quarantined_records: list[QuarantineRecord] = field(default_factory=list)
    total_rows_read: int = 0

    @property
    def valid_count(self) -> int:
        return len(self.valid_records)

    @property
    def quarantined_count(self) -> int:
        return len(self.quarantined_records)


class CSVLoader:
    """
    Robust CSV loader that validates headers, constructs typed models,
    and quarantines invalid rows with rich diagnostic reasons.
    """

    def __init__(
        self,
        entity_type: EntityType,
        run_id: Optional[str] = None,
        delimiter: Optional[str] = None,
        encoding: str = "utf-8-sig",
        allow_unknown_columns: bool = False,
    ) -> None:
        """
        Initialize the CSVLoader.

        Args:
            entity_type: EntityType.CUSTOMER or EntityType.PRODUCT.
            run_id: Unique run/batch identifier. Defaults to new UUID4.
            delimiter: Explicit delimiter (e.g. ',' or ';'). If None, sniffs or defaults to ','.
            encoding: Text encoding. 'utf-8-sig' automatically strips any UTF-8 BOM.
            allow_unknown_columns: If False, extra columns not in the schema will be flagged.
        """
        self.entity_type = entity_type
        self.run_id = run_id or str(uuid.uuid4())
        self.delimiter = delimiter
        self.encoding = encoding
        self.allow_unknown_columns = allow_unknown_columns

        if self.entity_type == EntityType.CUSTOMER:
            self.required_cols = CUSTOMER_REQUIRED_HEADER_COLS
            self.known_cols = CUSTOMER_KNOWN_COLS
            self.model_cls = CustomerSourceRecord
        elif self.entity_type == EntityType.PRODUCT:
            self.required_cols = PRODUCT_REQUIRED_HEADER_COLS
            self.known_cols = PRODUCT_KNOWN_COLS
            self.model_cls = ProductSourceRecord
        else:
            raise ValueError(f"Unsupported entity type: {entity_type}")

    def load_from_path(self, path: Union[str, Path]) -> IngestionResult:
        """
        Load and validate a CSV file from a disk path.

        Args:
            path: String or Path to the CSV file.

        Returns:
            IngestionResult containing valid and quarantined records.

        Raises:
            IngestionIOError: If file does not exist or cannot be opened.
            EmptyInputError: If file is 0 bytes or completely blank.
            SchemaMismatchError: If required header columns are missing or unknown columns are present.
        """
        file_path = Path(path)
        if not file_path.exists():
            raise IngestionIOError(f"Input file not found at: {file_path}")

        try:
            content = file_path.read_text(encoding=self.encoding)
        except Exception as e:
            raise IngestionIOError(f"Failed to read file {file_path}: {e}") from e

        return self.load_from_string(content, file_path=file_path)

    def load_from_string(
        self, content: str, file_path: Optional[Path] = None
    ) -> IngestionResult:
        """
        Parse CSV content from an in-memory string. Useful for testing and streaming.
        """
        source_path = file_path or Path("<in-memory>")
        stripped_content = content.strip()
        if not stripped_content:
            raise EmptyInputError(f"Input content from {source_path} is empty (0 bytes).")

        # Detect delimiter if not explicitly provided
        active_delimiter = self.delimiter or ","
        first_line = stripped_content.splitlines()[0]
        if self.delimiter is None and "\t" in first_line and "," not in first_line:
            active_delimiter = "\t"
        elif self.delimiter is None and ";" in first_line and "," not in first_line:
            active_delimiter = ";"

        reader = csv.reader(StringIO(stripped_content), delimiter=active_delimiter)

        try:
            raw_header = next(reader, None)
        except csv.Error as e:
            raise EmptyInputError(f"Could not parse header from {source_path}: {e}") from e

        if raw_header is None:
            raise EmptyInputError(f"Input file {source_path} has no header line.")

        # Clean header column names (trim and remove whitespace)
        cleaned_headers = [c.strip() for c in raw_header]

        # Check required columns in header
        missing_required = self.required_cols - set(cleaned_headers)
        if missing_required:
            raise SchemaMismatchError(
                f"Schema validation failed for {self.entity_type.value}: "
                f"Missing mandatory header column(s): {sorted(list(missing_required))}. "
                f"Received headers: {cleaned_headers}."
            )

        # Check unexpected extra columns if strict mode is active
        if not self.allow_unknown_columns:
            unknown_cols = set(cleaned_headers) - self.known_cols
            if unknown_cols:
                raise SchemaMismatchError(
                    f"Unexpected schema drift detected for {self.entity_type.value}: "
                    f"Found unknown column(s): {sorted(list(unknown_cols))}. "
                    f"Set allow_unknown_columns=True if this schema change is intentional."
                )

        result = IngestionResult(
            entity_type=self.entity_type,
            run_id=self.run_id,
            file_path=source_path,
        )

        expected_col_count = len(cleaned_headers)
        seen_source_keys: set[tuple[str, str]] = set()

        line_number = 1  # Header was line 1
        for row in reader:
            line_number += 1
            result.total_rows_read += 1

            # Check for empty lines
            if not row or all(c.strip() == "" for c in row):
                continue

            # Check for malformed rows (unequal column count)
            if len(row) != expected_col_count:
                quarantine_id = f"Q-{uuid.uuid4().hex[:12]}"
                result.quarantined_records.append(
                    QuarantineRecord(
                        quarantine_id=quarantine_id,
                        run_id=self.run_id,
                        entity_type=self.entity_type,
                        source_system="UNKNOWN",
                        source_record_id=f"LINE_{line_number}",
                        raw_payload={"raw_line_values": row, "line_number": line_number},
                        rejection_reasons=[
                            ValidationErrorDetail(
                                field="_row_",
                                code=RejectionCode.MALFORMED_ROW,
                                message=(
                                    f"Malformed row at line {line_number}: expected "
                                    f"{expected_col_count} columns, but found {len(row)}."
                                ),
                                invalid_value=row,
                            )
                        ],
                    )
                )
                continue

            # Map to dictionary
            row_dict = dict(zip(cleaned_headers, row))

            # Validate against entity model
            record, errors = self.model_cls.from_row(row_dict)

            # Extract source key for duplicate detection
            src_sys = (row_dict.get("source_system") or "UNKNOWN").strip()
            src_id = (row_dict.get("source_record_id") or f"LINE_{line_number}").strip()
            source_key = (src_sys, src_id)

            # Check for duplicate source key within the same ingestion batch
            if source_key in seen_source_keys:
                dup_error = ValidationErrorDetail(
                    field="source_record_id",
                    code=RejectionCode.DUPLICATE_SOURCE_KEY,
                    message=(
                        f"Duplicate source key detected in batch: system '{src_sys}', "
                        f"id '{src_id}' was already processed earlier in this file."
                    ),
                    invalid_value=src_id,
                )
                errors.append(dup_error)
                record = None
            else:
                seen_source_keys.add(source_key)

            if errors or record is None:
                quarantine_id = f"Q-{uuid.uuid4().hex[:12]}"
                result.quarantined_records.append(
                    QuarantineRecord(
                        quarantine_id=quarantine_id,
                        run_id=self.run_id,
                        entity_type=self.entity_type,
                        source_system=src_sys,
                        source_record_id=src_id,
                        raw_payload=row_dict,
                        rejection_reasons=errors,
                    )
                )
            else:
                result.valid_records.append(record)

        return result

