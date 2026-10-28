"""Ingestion package for safe CSV and JSON loading."""

from deduplication.ingestion.loader import (
    CSVLoader,
    EmptyInputError,
    IngestionIOError,
    IngestionResult,
    SchemaMismatchError,
)

__all__ = [
    "CSVLoader",
    "EmptyInputError",
    "IngestionIOError",
    "IngestionResult",
    "SchemaMismatchError",
]

