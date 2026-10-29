"""FastAPI router mapping HTTP requests to pipeline service methods."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from deduplication.api.models import (
    AvailableFilesResponse,
    DashboardSummary,
    DataQualitySummaryResponse,
    HealthResponse,
    RecordListResponse,
    ReviewActionRequest,
    ReviewActionResponse,
    ReviewQueueResponse,
    RunCreateRequest,
    RunCreateResponse,
    RunListResponse,
    RunSummary,
)
from deduplication.api.service import PipelineService

router = APIRouter(prefix="/api", tags=["deduplication"])
_service = PipelineService()


@router.get("/health", response_model=HealthResponse)
def get_health():
    """Check backend and SQLite database connectivity status."""
    return _service.get_health()


@router.get("/dashboard/summary", response_model=DashboardSummary)
def get_dashboard_summary():
    """Retrieve aggregate KPI metrics and distribution counts for the overview dashboard."""
    try:
        return _service.get_dashboard_summary()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load dashboard metrics: {str(e)}",
        )


@router.get("/runs", response_model=RunListResponse)
def list_runs(
    entity_type: Optional[str] = Query(None, description="Filter by CUSTOMER or PRODUCT"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by RUNNING, COMPLETED, FAILED"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Retrieve paginated pipeline execution history."""
    try:
        return _service.list_runs(entity_type=entity_type, status=status_filter, page=page, page_size=page_size)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch runs: {str(e)}",
        )


@router.get("/runs/{run_id}", response_model=RunSummary)
def get_run(run_id: str):
    """Retrieve details for a single pipeline run."""
    run = _service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Run '{run_id}' not found")
    return run


@router.post("/runs", response_model=RunCreateResponse)
def trigger_run(request: RunCreateRequest):
    """Execute deduplication pipeline on an input CSV file."""
    try:
        result = _service.trigger_pipeline_run(
            entity_type=request.entity_type,
            input_file=request.input_file,
            force_full_pairwise=request.force_full_pairwise,
        )
        return RunCreateResponse(
            run_id=result["run_id"],
            entity_type=result["entity_type"],
            status=result["status"],
            message=result["message"],
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Pipeline execution error: {str(e)}")


@router.get("/files/available", response_model=AvailableFilesResponse)
def list_available_files():
    """List CSV files available on disk for deduplication."""
    return {"files": _service.list_available_files()}


@router.get("/records", response_model=RecordListResponse)
def list_records(
    entity_type: str = Query("customer", description="'customer' or 'product'"),
    search: Optional[str] = Query(None, description="Search by name, email, phone, sku, etc."),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Retrieve paginated golden master records for Customers or Products."""
    if entity_type.lower() not in ["customer", "product"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="entity_type must be 'customer' or 'product'",
        )
    try:
        return _service.list_records(
            entity_type=entity_type, search=search, page=page, page_size=page_size
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch records: {str(e)}",
        )


@router.get("/records/{entity_type}/{master_id}/lineage")
def get_record_lineage(entity_type: str, master_id: str):
    """Fetch complete source record lineage and merge attribution for a specific master record."""
    if entity_type.lower() not in ["customer", "product"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="entity_type must be 'customer' or 'product'",
        )
    data = _service.get_master_lineage(entity_type=entity_type, master_id=master_id)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Master record not found")
    return data


@router.get("/review-queue", response_model=ReviewQueueResponse)
def list_review_queue(
    entity_type: Optional[str] = Query(None, description="'customer' or 'product'"),
    status_filter: Optional[str] = Query(None, alias="status", description="'PENDING', 'APPROVED', 'REJECTED'"),
    search: Optional[str] = Query(None, description="Search reasons or source ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Retrieve paginated ambiguous or flagged candidate pairs awaiting human manual review."""
    try:
        return _service.list_review_queue(
            entity_type=entity_type, status=status_filter, search=search, page=page, page_size=page_size
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch review queue: {str(e)}",
        )


@router.post("/review-queue/{review_id}/action", response_model=ReviewActionResponse)
def update_review_action(review_id: str, request: ReviewActionRequest):
    """Update human review decision for an ambiguous pair."""
    try:
        res = _service.update_review_action(
            review_id=review_id, new_status=request.status, notes=request.notes
        )
        if not res:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Review item '{review_id}' not found",
            )
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update review item: {str(e)}",
        )


@router.get("/data-quality/summary", response_model=DataQualitySummaryResponse)
def get_data_quality_summary(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)
):
    """Retrieve quarantine rate, rejection error code breakdown, and recent quarantined records."""
    try:
        return _service.get_data_quality_summary(page=page, page_size=page_size)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch data quality summary: {str(e)}",
        )


@router.get("/reports/{run_id}")
def get_run_report(run_id: str):
    """Retrieve structured operational validation report and ground truth evaluation."""
    data = _service.get_run_report(run_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report for run '{run_id}' not found",
        )
    return data


@router.get("/settings")
def get_settings():
    """Retrieve active deduplication rules, similarity thresholds, and source priorities."""
    cust_rules_path = Path("config/customer_rules.json")
    prod_rules_path = Path("config/product_rules.json")

    cust_rules = {}
    if cust_rules_path.exists():
        try:
            cust_rules = json.loads(cust_rules_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    prod_rules = {}
    if prod_rules_path.exists():
        try:
            prod_rules = json.loads(prod_rules_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    return {
        "customer_rules": cust_rules,
        "product_rules": prod_rules,
        "database_path": str(_service.db_path),
        "output_directory": str(_service.output_dir),
    }

