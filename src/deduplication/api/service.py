"""Service layer bridging FastAPI to DeduplicationPipeline and SQLite storage."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import threading
from typing import Any, Optional

from deduplication.orchestration import DeduplicationPipeline
from deduplication.reporting.validation_report import ReportGenerator
from deduplication.schemas.common import EntityType, RunStatus
from deduplication.storage.repository import SQLiteRepository

DEFAULT_DB_PATH = Path(os.environ.get("DEDUPLICATION_DB_PATH", "output/pipeline.db"))
DEFAULT_OUTPUT_DIR = Path(os.environ.get("DEDUPLICATION_OUTPUT_DIR", "output"))


class PipelineService:
    """Thread-safe facade for reading pipeline data and launching background deduplication runs."""

    def __init__(self, db_path: Optional[Path] = None, output_dir: Optional[Path] = None) -> None:
        self.db_path = db_path or DEFAULT_DB_PATH
        self.output_dir = output_dir or DEFAULT_OUTPUT_DIR
        self._execution_lock = threading.Lock()
        self.repository = SQLiteRepository(self.db_path)

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def get_health(self) -> dict[str, Any]:
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM pipeline_runs")
                total_runs = cursor.fetchone()[0]
                connected = True
        except Exception:
            total_runs = 0
            connected = False

        return {
            "status": "ok",
            "version": "0.1.0",
            "database": str(self.db_path),
            "database_connected": connected,
            "total_runs": total_runs,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_dashboard_summary(self) -> dict[str, Any]:
        """Aggregate high-level operational KPIs and charts across runs and entities."""
        with self.get_connection() as conn:
            # Aggregate run stats
            runs_cur = conn.execute(
                """
                SELECT 
                    COUNT(*) as total_runs,
                    COALESCE(SUM(input_count), 0) as total_input,
                    COALESCE(SUM(valid_count), 0) as total_valid,
                    COALESCE(SUM(quarantined_count), 0) as total_quarantined,
                    COALESCE(SUM(exact_match_count), 0) as total_exact,
                    COALESCE(SUM(probable_match_count), 0) as total_probable,
                    COALESCE(SUM(review_count), 0) as total_review
                FROM pipeline_runs
                """
            )
            r_row = dict(runs_cur.fetchone())

            # Count actual golden master records in tables
            cust_cur = conn.execute("SELECT COUNT(*) FROM master_customers")
            total_master_cust = cust_cur.fetchone()[0]

            prod_cur = conn.execute("SELECT COUNT(*) FROM master_products")
            total_master_prod = prod_cur.fetchone()[0]

            total_masters = total_master_cust + total_master_prod

            # Pending review queue count
            rev_cur = conn.execute("SELECT COUNT(*) FROM manual_review_queue WHERE status = 'PENDING'")
            pending_reviews = rev_cur.fetchone()[0]

            # Latest run
            latest_cur = conn.execute(
                "SELECT * FROM pipeline_runs ORDER BY started_at DESC LIMIT 1"
            )
            latest_row = latest_cur.fetchone()
            latest_run = dict(latest_row) if latest_row else None

            # Runs by entity
            entity_cur = conn.execute(
                "SELECT entity_type, COUNT(*) FROM pipeline_runs GROUP BY entity_type"
            )
            runs_by_entity = {row[0]: row[1] for row in entity_cur.fetchall()}

            # Status distribution
            status_cur = conn.execute(
                "SELECT status, COUNT(*) FROM pipeline_runs GROUP BY status"
            )
            status_distribution = {row[0]: row[1] for row in status_cur.fetchall()}

            # Rejection distribution by code
            q_cur = conn.execute("SELECT rejection_reasons FROM quarantine_records")
            rejection_distribution: dict[str, int] = {}
            for row in q_cur.fetchall():
                try:
                    reasons = json.loads(row[0])
                    for r in reasons:
                        code = r.get("code", "UNKNOWN")
                        rejection_distribution[code] = rejection_distribution.get(code, 0) + 1
                except Exception:
                    pass

            return {
                "total_records_processed": r_row["total_input"],
                "valid_records_processed": r_row["total_valid"],
                "quarantined_records": r_row["total_quarantined"],
                "golden_masters_created": total_masters,
                "exact_merges": r_row["total_exact"],
                "probable_merges": r_row["total_probable"],
                "manual_reviews_pending": pending_reviews,
                "total_runs_count": r_row["total_runs"],
                "latest_run": latest_run,
                "runs_by_entity": runs_by_entity,
                "status_distribution": status_distribution,
                "rejection_distribution": rejection_distribution,
            }

    def list_runs(
        self,
        entity_type: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List pipeline execution history with filtering and pagination."""
        offset = (page - 1) * page_size
        where_clauses = []
        params: list[Any] = []

        if entity_type and entity_type.upper() in ["CUSTOMER", "PRODUCT"]:
            where_clauses.append("entity_type = ?")
            params.append(entity_type.upper())

        if status and status.upper() in ["RUNNING", "COMPLETED", "FAILED"]:
            where_clauses.append("status = ?")
            params.append(status.upper())

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        with self.get_connection() as conn:
            count_cur = conn.execute(f"SELECT COUNT(*) FROM pipeline_runs {where_sql}", params)
            total = count_cur.fetchone()[0]

            query = f"""
            SELECT * FROM pipeline_runs 
            {where_sql}
            ORDER BY started_at DESC 
            LIMIT ? OFFSET ?
            """
            rows = conn.execute(query, params + [page_size, offset]).fetchall()
            items = [dict(r) for r in rows]

            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
            }

    def get_run(self, run_id: str) -> Optional[dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT * FROM pipeline_runs WHERE run_id = ?", (run_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def list_records(
        self,
        entity_type: str,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Retrieve paginated master records for Customers or Products."""
        offset = (page - 1) * page_size
        is_customer = entity_type.lower() == "customer"
        table = "master_customers" if is_customer else "master_products"

        where_clauses = []
        params: list[Any] = []

        if search and search.strip():
            term = f"%{search.strip()}%"
            if is_customer:
                where_clauses.append(
                    "(first_name LIKE ? OR last_name LIKE ? OR primary_email LIKE ? OR primary_phone LIKE ? OR tax_id LIKE ? OR city LIKE ?)"
                )
                params.extend([term, term, term, term, term, term])
            else:
                where_clauses.append(
                    "(product_name LIKE ? OR brand LIKE ? OR primary_sku LIKE ? OR primary_upc_ean LIKE ? OR category LIKE ?)"
                )
                params.extend([term, term, term, term, term])

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        with self.get_connection() as conn:
            count_cur = conn.execute(f"SELECT COUNT(*) FROM {table} {where_sql}", params)
            total = count_cur.fetchone()[0]

            # Join with lineage count to see how many source records contributed to this master
            entity_enum_val = "CUSTOMER" if is_customer else "PRODUCT"
            query = f"""
            SELECT m.*, 
                   COALESCE(l.src_count, 1) as source_count
            FROM {table} m
            LEFT JOIN (
                SELECT master_id, COUNT(*) as src_count 
                FROM record_lineage 
                WHERE entity_type = '{entity_enum_val}'
                GROUP BY master_id
            ) l ON m.master_id = l.master_id
            {where_sql}
            ORDER BY m.updated_at DESC
            LIMIT ? OFFSET ?
            """
            rows = conn.execute(query, params + [page_size, offset]).fetchall()

            items = []
            for r in rows:
                item_dict = dict(r)
                # Parse JSON arrays if present
                for json_col in ["secondary_emails", "secondary_phones", "secondary_skus"]:
                    if json_col in item_dict and isinstance(item_dict[json_col], str):
                        try:
                            item_dict[json_col] = json.loads(item_dict[json_col])
                        except Exception:
                            item_dict[json_col] = []
                items.append(item_dict)

            return {
                "entity_type": entity_type.lower(),
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
            }

    def get_master_lineage(self, entity_type: str, master_id: str) -> Optional[dict[str, Any]]:
        """Retrieve master record details and all contributing source record lineages."""
        is_customer = entity_type.lower() == "customer"
        table = "master_customers" if is_customer else "master_products"

        with self.get_connection() as conn:
            m_cur = conn.execute(f"SELECT * FROM {table} WHERE master_id = ?", (master_id,))
            m_row = m_cur.fetchone()
            if not m_row:
                return None

            master_dict = dict(m_row)
            for json_col in ["secondary_emails", "secondary_phones", "secondary_skus"]:
                if json_col in master_dict and isinstance(master_dict[json_col], str):
                    try:
                        master_dict[json_col] = json.loads(master_dict[json_col])
                    except Exception:
                        master_dict[json_col] = []

            lin_cur = conn.execute(
                """
                SELECT * FROM record_lineage 
                WHERE master_id = ? 
                ORDER BY created_at ASC
                """,
                (master_id,),
            )
            lineage_items = []
            for r in lin_cur.fetchall():
                ld = dict(r)
                if isinstance(ld.get("merge_reasons"), str):
                    try:
                        ld["merge_reasons"] = json.loads(ld["merge_reasons"])
                    except Exception:
                        ld["merge_reasons"] = [ld["merge_reasons"]]
                lineage_items.append(ld)

            return {
                "master_record": master_dict,
                "lineage": lineage_items,
            }

    def list_review_queue(
        self,
        entity_type: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Fetch manual review queue items with filter by entity and status."""
        offset = (page - 1) * page_size
        where_clauses = []
        params: list[Any] = []

        if entity_type and entity_type.upper() in ["CUSTOMER", "PRODUCT"]:
            where_clauses.append("entity_type = ?")
            params.append(entity_type.upper())

        if status:
            where_clauses.append("status = ?")
            params.append(status.upper())

        if search and search.strip():
            term = f"%{search.strip()}%"
            where_clauses.append("(source_record_id LIKE ? OR source_system LIKE ? OR reasons LIKE ?)")
            params.extend([term, term, term])

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        with self.get_connection() as conn:
            count_cur = conn.execute(f"SELECT COUNT(*) FROM manual_review_queue {where_sql}", params)
            total = count_cur.fetchone()[0]

            query = f"""
            SELECT * FROM manual_review_queue
            {where_sql}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """
            rows = conn.execute(query, params + [page_size, offset]).fetchall()
            items = []
            for r in rows:
                item_dict = dict(r)
                # Parse reasons JSON
                if isinstance(item_dict.get("reasons"), str):
                    try:
                        parsed_reasons = json.loads(item_dict["reasons"])
                        item_dict["reasons"] = parsed_reasons if isinstance(parsed_reasons, list) else [parsed_reasons]
                    except Exception:
                        item_dict["reasons"] = [item_dict["reasons"]]
                else:
                    item_dict["reasons"] = []
                items.append(item_dict)

            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
            }

    def update_review_action(
        self, review_id: str, new_status: str, notes: Optional[str] = None
    ) -> Optional[dict[str, Any]]:
        """Update review item status (APPROVED, REJECTED, RESOLVED)."""
        valid_statuses = {"APPROVED", "REJECTED", "RESOLVED", "PENDING"}
        normalized_status = new_status.upper().strip()
        if normalized_status not in valid_statuses:
            raise ValueError(f"Invalid status: {new_status}. Must be one of {valid_statuses}")

        with self.get_connection() as conn:
            cur = conn.execute("SELECT * FROM manual_review_queue WHERE review_id = ?", (review_id,))
            row = cur.fetchone()
            if not row:
                return None

            conn.execute(
                "UPDATE manual_review_queue SET status = ? WHERE review_id = ?",
                (normalized_status, review_id),
            )
            conn.commit()

        return {
            "review_id": review_id,
            "status": normalized_status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "message": f"Review item marked as {normalized_status}." + (f" Note: {notes}" if notes else ""),
        }

    def get_data_quality_summary(self, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        """Aggregate data-quality error codes, distribution, and recent quarantined items."""
        offset = (page - 1) * page_size
        with self.get_connection() as conn:
            # Total quarantined
            total_q_cur = conn.execute("SELECT COUNT(*) FROM quarantine_records")
            total_quarantined = total_q_cur.fetchone()[0]

            # Total accepted valid
            valid_cur = conn.execute("SELECT COALESCE(SUM(valid_count), 0) FROM pipeline_runs")
            total_accepted = valid_cur.fetchone()[0]

            total_records = total_accepted + total_quarantined
            q_rate = (total_quarantined / total_records * 100.0) if total_records > 0 else 0.0

            # Rejection codes distribution
            q_rows = conn.execute("SELECT rejection_reasons FROM quarantine_records").fetchall()
            code_counts: dict[str, int] = {}
            field_counts: dict[str, int] = {}
            for r in q_rows:
                try:
                    reasons = json.loads(r[0])
                    for item in reasons:
                        code = item.get("code", "UNKNOWN")
                        field = item.get("field", "unknown")
                        code_counts[code] = code_counts.get(code, 0) + 1
                        field_counts[field] = field_counts.get(field, 0) + 1
                except Exception:
                    pass

            # Recent quarantined records paginated
            recent_rows = conn.execute(
                """
                SELECT * FROM quarantine_records 
                ORDER BY quarantined_at DESC 
                LIMIT ? OFFSET ?
                """,
                (page_size, offset),
            ).fetchall()

            recent_items = []
            for r in recent_rows:
                rd = dict(r)
                if isinstance(rd.get("raw_payload"), str):
                    try:
                        rd["raw_payload"] = json.loads(rd["raw_payload"])
                    except Exception:
                        pass
                if isinstance(rd.get("rejection_reasons"), str):
                    try:
                        rd["rejection_reasons"] = json.loads(rd["rejection_reasons"])
                    except Exception:
                        pass
                recent_items.append(rd)

            return {
                "total_quarantined": total_quarantined,
                "quarantine_rate_pct": round(q_rate, 2),
                "rejection_code_counts": code_counts,
                "rejections_by_field": field_counts,
                "recent_quarantines": recent_items,
                "total_accepted": total_accepted,
            }

    def get_run_report(self, run_id: str) -> Optional[dict[str, Any]]:
        """Generate structured validation report for a run."""
        reporter = ReportGenerator(db_path=self.db_path)
        with self.get_connection() as conn:
            cur = conn.execute("SELECT entity_type FROM pipeline_runs WHERE run_id = ?", (run_id,))
            row = cur.fetchone()
            if not row:
                return None
            entity_type = row[0].lower()

        # Check for possible ground truth file
        gt_candidate = Path(f"data/sample/{entity_type}s_500_ground_truth.json")
        gt_path = gt_candidate if gt_candidate.exists() else None

        try:
            report_data = reporter.generate_run_report(run_id, ground_truth_path=gt_path)
            report_data["markdown"] = reporter.format_markdown_report(report_data)
            return report_data
        except Exception as e:
            return {
                "error": str(e),
                "run_id": run_id,
            }

    def list_available_files(self) -> list[dict[str, Any]]:
        """List CSV files available for ingestion."""
        found_files = []
        search_dirs = [Path("data/sample"), Path("data/synthetic"), Path(".")]
        seen_paths = set()

        for d in search_dirs:
            if d.exists():
                for p in d.glob("*.csv"):
                    if p.is_file() and p.resolve() not in seen_paths:
                        seen_paths.add(p.resolve())
                        fn = p.name.lower()
                        hint = "customer" if "cust" in fn else ("product" if "prod" in fn else "unknown")
                        found_files.append({
                            "path": str(p).replace("\\", "/"),
                            "filename": p.name,
                            "size_bytes": p.stat().st_size,
                            "entity_hint": hint,
                            "is_sample": "sample" in str(p),
                        })

        return sorted(found_files, key=lambda f: f["filename"])

    def trigger_pipeline_run(
        self, entity_type: str, input_file: str, force_full_pairwise: bool = False
    ) -> dict[str, Any]:
        """
        Execute a pipeline run safely with mutual exclusion lock
        to prevent concurrent writes to the same SQLite database.
        """
        entity = EntityType.CUSTOMER if entity_type.lower() == "customer" else EntityType.PRODUCT
        file_path = Path(input_file)
        if not file_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")

        acquired = self._execution_lock.acquire(blocking=False)
        if not acquired:
            raise RuntimeError("Another pipeline run is currently in progress. Please wait for it to complete.")

        out_dir = self.output_dir / entity_type.lower()
        out_dir.mkdir(parents=True, exist_ok=True)

        try:
            pipeline = DeduplicationPipeline(
                entity_type=entity,
                db_path=self.db_path,
                output_dir=out_dir,
            )
            metrics = pipeline.run(input_path=file_path, force_full_pairwise=force_full_pairwise)
            return {
                "run_id": metrics.run_id,
                "entity_type": entity.value,
                "status": metrics.status.value,
                "input_count": metrics.input_count,
                "valid_count": metrics.valid_count,
                "quarantined_count": metrics.quarantined_count,
                "master_records_created": metrics.master_records_created,
                "elapsed_seconds": metrics.elapsed_seconds,
                "message": f"Pipeline run completed successfully in {metrics.elapsed_seconds:.2f}s",
            }
        finally:
            self._execution_lock.release()

