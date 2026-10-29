"""Integration tests for FastAPI backend endpoints."""

from fastapi.testclient import TestClient
import pytest

from deduplication.api.app import app
from deduplication.api.service import PipelineService


@pytest.fixture
def client():
    # Initialize DB schema before test client runs
    service = PipelineService()
    service.repository._init_db()
    with TestClient(app) as c:
        yield c


def test_api_health(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "database_connected" in data


def test_api_dashboard_summary(client: TestClient):
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_records_processed" in data
    assert "golden_masters_created" in data
    assert "quarantined_records" in data
    assert "runs_by_entity" in data


def test_api_runs_list_and_detail(client: TestClient):
    response = client.get("/api/runs")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data

    # Test 404 for nonexistent run ID
    res_404 = client.get("/api/runs/NON_EXISTENT_RUN_ID")
    assert res_404.status_code == 404


def test_api_records_customer_and_product(client: TestClient):
    # Customer records
    res_cust = client.get("/api/records?entity_type=customer&page=1&page_size=5")
    assert res_cust.status_code == 200
    data_cust = res_cust.json()
    assert data_cust["entity_type"] == "customer"
    assert "items" in data_cust

    # Product records
    res_prod = client.get("/api/records?entity_type=product&page=1&page_size=5")
    assert res_prod.status_code == 200
    data_prod = res_prod.json()
    assert data_prod["entity_type"] == "product"

    # Invalid entity type
    res_invalid = client.get("/api/records?entity_type=invalid")
    assert res_invalid.status_code == 400


def test_api_review_queue(client: TestClient):
    response = client.get("/api/review-queue")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


def test_api_data_quality_summary(client: TestClient):
    response = client.get("/api/data-quality/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_quarantined" in data
    assert "rejection_code_counts" in data


def test_api_files_available(client: TestClient):
    response = client.get("/api/files/available")
    assert response.status_code == 200
    data = response.json()
    assert "files" in data
    assert isinstance(data["files"], list)


def test_api_settings(client: TestClient):
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert "customer_rules" in data
    assert "product_rules" in data
    assert "database_path" in data

