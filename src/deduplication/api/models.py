"""Pydantic data transfer schemas for FastAPI endpoints."""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    database_connected: bool
    total_runs: int
    timestamp: str


class KpiMetric(BaseModel):
    value: int | float
    formatted: str
    label: str
    change_pct: Optional[float] = None
    trend: Optional[str] = None


class DashboardSummary(BaseModel):
    total_records_processed: int
    valid_records_processed: int
    quarantined_records: int
    golden_masters_created: int
    exact_merges: int
    probable_merges: int
    manual_reviews_pending: int
    total_runs_count: int
    latest_run: Optional[dict[str, Any]] = None
    runs_by_entity: dict[str, int]
    status_distribution: dict[str, int]
    rejection_distribution: dict[str, int]


class RunSummary(BaseModel):
    run_id: str
    entity_type: str
    started_at: str
    ended_at: Optional[str] = None
    status: str
    input_count: int
    valid_count: int
    quarantined_count: int
    exact_match_count: int
    probable_match_count: int
    review_count: int
    distinct_count: int
    elapsed_seconds: Optional[float] = None
    error_summary: Optional[str] = None


class RunListResponse(BaseModel):
    items: list[RunSummary]
    total: int
    page: int
    page_size: int


class RunCreateRequest(BaseModel):
    entity_type: str = Field(description="'customer' or 'product'")
    input_file: str = Field(description="Relative or absolute path to CSV file")
    force_full_pairwise: bool = False


class RunCreateResponse(BaseModel):
    run_id: str
    entity_type: str
    status: str
    message: str


class MasterCustomerItem(BaseModel):
    master_id: str
    first_name: Optional[str] = None
    last_name: str
    primary_email: Optional[str] = None
    secondary_emails: list[str] = []
    primary_phone: Optional[str] = None
    secondary_phones: list[str] = []
    street_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    tax_id: Optional[str] = None
    date_of_birth: Optional[str] = None
    created_at: str
    updated_at: str
    record_version: int
    source_count: int = 1


class MasterProductItem(BaseModel):
    master_id: str
    product_name: str
    brand: str
    primary_sku: Optional[str] = None
    secondary_skus: list[str] = []
    primary_upc_ean: Optional[str] = None
    category: Optional[str] = None
    unit_price: Optional[float] = None
    currency: Optional[str] = "USD"
    created_at: str
    updated_at: str
    record_version: int
    source_count: int = 1


class RecordListResponse(BaseModel):
    entity_type: str
    items: list[dict[str, Any]]
    total: int
    page: int
    page_size: int


class LineageRecordItem(BaseModel):
    lineage_id: str
    run_id: str
    entity_type: str
    source_system: str
    source_record_id: str
    master_id: str
    decision: str
    match_rule_id: str
    confidence_score: float
    merge_reasons: list[str]
    created_at: str


class MasterLineageDetail(BaseModel):
    master_record: dict[str, Any]
    lineage: list[LineageRecordItem]


class ReviewItem(BaseModel):
    review_id: str
    run_id: str
    entity_type: str
    source_system: str
    source_record_id: str
    candidate_master_id: Optional[str] = None
    similarity_score: Optional[float] = None
    reasons: list[str]
    hard_conflicts: list[str] = []
    status: str
    created_at: str


class ReviewQueueResponse(BaseModel):
    items: list[ReviewItem]
    total: int
    page: int
    page_size: int


class ReviewActionRequest(BaseModel):
    status: str = Field(description="'APPROVED', 'REJECTED', or 'RESOLVED'")
    notes: Optional[str] = None


class ReviewActionResponse(BaseModel):
    review_id: str
    status: str
    updated_at: str
    message: str


class QuarantineItem(BaseModel):
    quarantine_id: str
    run_id: str
    entity_type: str
    source_system: str
    source_record_id: str
    raw_payload: dict[str, Any]
    rejection_reasons: list[dict[str, Any]]
    quarantined_at: str


class DataQualitySummaryResponse(BaseModel):
    total_quarantined: int
    quarantine_rate_pct: float
    rejection_code_counts: dict[str, int]
    rejections_by_field: dict[str, int]
    recent_quarantines: list[QuarantineItem]
    total_accepted: int


class AvailableFileItem(BaseModel):
    path: str
    filename: str
    size_bytes: int
    entity_hint: str
    is_sample: bool


class AvailableFilesResponse(BaseModel):
    files: list[AvailableFileItem]

