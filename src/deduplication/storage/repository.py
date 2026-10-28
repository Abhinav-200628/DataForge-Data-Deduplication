"""
SQLite storage repository providing transactional publishing, run history,
unique constraints, idempotent reruns, and safe file export.
"""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from typing import Any, Optional, Sequence, Union

from deduplication.lineage.models import ManualReviewItem, RecordLineage
from deduplication.schemas.common import EntityType, RunStatus
from deduplication.schemas.quarantine import QuarantineRecord
from deduplication.survivorship.models import MasterCustomer, MasterProduct

_SCHEMA_FILE = Path(__file__).parent / "schema.sql"


class SQLiteRepository:
    """Manages SQLite persistence with atomic transactions and idempotent upserts."""

    def __init__(self, db_path: Union[str, Path] = "pipeline.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_db(self) -> None:
        """Create tables and indexes if they do not exist."""
        schema_sql = _SCHEMA_FILE.read_text(encoding="utf-8")
        with self._get_connection() as conn:
            conn.executescript(schema_sql)

    def record_run_start(self, run_id: str, entity_type: EntityType, started_at: str) -> None:
        """Record the initiation of a pipeline run."""
        sql = """
        INSERT INTO pipeline_runs (run_id, entity_type, started_at, status)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(run_id) DO UPDATE SET
            started_at = excluded.started_at,
            status = excluded.status;
        """
        with self._get_connection() as conn:
            conn.execute(sql, (run_id, entity_type.value, started_at, RunStatus.RUNNING.value))

    def record_run_finish(
        self,
        run_id: str,
        status: RunStatus,
        ended_at: str,
        input_count: int,
        valid_count: int,
        quarantined_count: int,
        exact_count: int,
        probable_count: int,
        review_count: int,
        distinct_count: int,
        elapsed_seconds: float,
        error_summary: Optional[str] = None,
    ) -> None:
        """Record the final summary metrics of a completed or failed pipeline run."""
        sql = """
        UPDATE pipeline_runs SET
            status = ?,
            ended_at = ?,
            input_count = ?,
            valid_count = ?,
            quarantined_count = ?,
            exact_match_count = ?,
            probable_match_count = ?,
            review_count = ?,
            distinct_count = ?,
            elapsed_seconds = ?,
            error_summary = ?
        WHERE run_id = ?;
        """
        with self._get_connection() as conn:
            conn.execute(
                sql,
                (
                    status.value,
                    ended_at,
                    input_count,
                    valid_count,
                    quarantined_count,
                    exact_count,
                    probable_count,
                    review_count,
                    distinct_count,
                    elapsed_seconds,
                    error_summary,
                    run_id,
                ),
            )

    def publish_pipeline_results(
        self,
        run_id: str,
        entity_type: EntityType,
        master_records: Sequence[Union[MasterCustomer, MasterProduct]],
        lineages: Sequence[RecordLineage],
        quarantines: Sequence[QuarantineRecord],
        review_items: Sequence[ManualReviewItem],
    ) -> None:
        """
        Atomically persist all output entities, lineage links, quarantines,
        and review queue items within a single database transaction.

        Uses UPSERT syntax to ensure rerun idempotency:
        re-running identical records updates existing records rather than duplicating them.
        """
        with self._get_connection() as conn:
            # 1. Publish Master Records
            if entity_type == EntityType.CUSTOMER:
                cust_sql = """
                INSERT INTO master_customers (
                    master_id, first_name, last_name, primary_email, secondary_emails,
                    primary_phone, secondary_phones, street_address, city, state,
                    postal_code, country, tax_id, date_of_birth, created_at, updated_at, record_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(master_id) DO UPDATE SET
                    first_name = excluded.first_name,
                    last_name = excluded.last_name,
                    primary_email = excluded.primary_email,
                    secondary_emails = excluded.secondary_emails,
                    primary_phone = excluded.primary_phone,
                    secondary_phones = excluded.secondary_phones,
                    street_address = excluded.street_address,
                    city = excluded.city,
                    state = excluded.state,
                    postal_code = excluded.postal_code,
                    country = excluded.country,
                    tax_id = excluded.tax_id,
                    date_of_birth = excluded.date_of_birth,
                    updated_at = excluded.updated_at,
                    record_version = master_customers.record_version + 1;
                """
                cust_rows = [
                    (
                        m.master_id,
                        m.first_name,
                        m.last_name,
                        m.primary_email,
                        json.dumps(m.secondary_emails),
                        m.primary_phone,
                        json.dumps(m.secondary_phones),
                        m.street_address,
                        m.city,
                        m.state,
                        m.postal_code,
                        m.country,
                        m.tax_id,
                        m.date_of_birth,
                        m.created_at,
                        m.updated_at,
                        m.record_version,
                    )
                    for m in master_records
                    if isinstance(m, MasterCustomer)
                ]
                conn.executemany(cust_sql, cust_rows)

            elif entity_type == EntityType.PRODUCT:
                prod_sql = """
                INSERT INTO master_products (
                    master_id, product_name, brand, primary_sku, secondary_skus,
                    primary_upc_ean, category, unit_price, currency, created_at, updated_at, record_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(master_id) DO UPDATE SET
                    product_name = excluded.product_name,
                    brand = excluded.brand,
                    primary_sku = excluded.primary_sku,
                    secondary_skus = excluded.secondary_skus,
                    primary_upc_ean = excluded.primary_upc_ean,
                    category = excluded.category,
                    unit_price = excluded.unit_price,
                    currency = excluded.currency,
                    updated_at = excluded.updated_at,
                    record_version = master_products.record_version + 1;
                """
                prod_rows = [
                    (
                        m.master_id,
                        m.product_name,
                        m.brand,
                        m.primary_sku,
                        json.dumps(m.secondary_skus),
                        m.primary_upc_ean,
                        m.category,
                        m.unit_price,
                        m.currency,
                        m.created_at,
                        m.updated_at,
                        m.record_version,
                    )
                    for m in master_records
                    if isinstance(m, MasterProduct)
                ]
                conn.executemany(prod_sql, prod_rows)

            # 2. Publish Lineage (Unique per source system + source record id)
            lineage_sql = """
            INSERT INTO record_lineage (
                lineage_id, run_id, entity_type, source_system, source_record_id,
                master_id, decision, match_rule_id, confidence_score, merge_reasons, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(entity_type, source_system, source_record_id) DO UPDATE SET
                master_id = excluded.master_id,
                decision = excluded.decision,
                match_rule_id = excluded.match_rule_id,
                confidence_score = excluded.confidence_score,
                merge_reasons = excluded.merge_reasons,
                run_id = excluded.run_id;
            """
            lineage_rows = [
                (
                    lin.lineage_id,
                    lin.run_id,
                    lin.entity_type.value,
                    lin.source_system,
                    lin.source_record_id,
                    lin.master_id,
                    lin.decision.value,
                    lin.match_rule_id,
                    lin.confidence_score,
                    lin.merge_reasons_json(),
                    lin.created_at,
                )
                for lin in lineages
            ]
            conn.executemany(lineage_sql, lineage_rows)

            # 3. Publish Quarantined Records
            quarantine_sql = """
            INSERT INTO quarantine_records (
                quarantine_id, run_id, entity_type, source_system, source_record_id,
                raw_payload, rejection_reasons, quarantined_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(entity_type, source_system, source_record_id) DO UPDATE SET
                raw_payload = excluded.raw_payload,
                rejection_reasons = excluded.rejection_reasons,
                run_id = excluded.run_id;
            """
            quarantine_rows = [
                (
                    q.quarantine_id,
                    q.run_id,
                    q.entity_type.value,
                    q.source_system,
                    q.source_record_id,
                    q.raw_payload_json(),
                    q.rejection_reasons_json(),
                    q.quarantined_at,
                )
                for q in quarantines
            ]
            conn.executemany(quarantine_sql, quarantine_rows)

            # 4. Publish Manual Review Queue
            review_sql = """
            INSERT INTO manual_review_queue (
                review_id, run_id, entity_type, source_system, source_record_id,
                candidate_master_id, similarity_score, reasons, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(entity_type, source_system, source_record_id, run_id) DO UPDATE SET
                similarity_score = excluded.similarity_score,
                reasons = excluded.reasons;
            """
            review_rows = [
                (
                    rev.review_id,
                    rev.run_id,
                    rev.entity_type.value,
                    rev.source_system,
                    rev.source_record_id,
                    rev.candidate_master_id,
                    rev.similarity_score,
                    rev.reasons_json(),
                    rev.status,
                    rev.created_at,
                )
                for rev in review_items
            ]
            conn.executemany(review_sql, review_rows)

    def export_outputs(self, output_dir: Union[str, Path], entity_type: EntityType) -> dict[str, Path]:
        """
        Export master records, lineage, quarantine, and review queues to CSV and JSON files.
        """
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        exported_files: dict[str, Path] = {}

        import pandas as pd

        with self._get_connection() as conn:
            # Export Master Records
            table_name = "master_customers" if entity_type == EntityType.CUSTOMER else "master_products"
            df_masters = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
            csv_masters = out_path / f"{entity_type.value.lower()}_masters.csv"
            json_masters = out_path / f"{entity_type.value.lower()}_masters.json"
            df_masters.to_csv(csv_masters, index=False)
            df_masters.to_json(json_masters, orient="records", indent=2)
            exported_files["masters_csv"] = csv_masters
            exported_files["masters_json"] = json_masters

            # Export Lineage
            df_lineage = pd.read_sql_query(
                "SELECT * FROM record_lineage WHERE entity_type = ?", conn, params=(entity_type.value,)
            )
            csv_lineage = out_path / f"{entity_type.value.lower()}_lineage.csv"
            json_lineage = out_path / f"{entity_type.value.lower()}_lineage.json"
            df_lineage.to_csv(csv_lineage, index=False)
            df_lineage.to_json(json_lineage, orient="records", indent=2)
            exported_files["lineage_csv"] = csv_lineage
            exported_files["lineage_json"] = json_lineage

            # Export Quarantine
            df_quarantine = pd.read_sql_query(
                "SELECT * FROM quarantine_records WHERE entity_type = ?", conn, params=(entity_type.value,)
            )
            csv_quarantine = out_path / f"{entity_type.value.lower()}_quarantine.csv"
            json_quarantine = out_path / f"{entity_type.value.lower()}_quarantine.json"
            df_quarantine.to_csv(csv_quarantine, index=False)
            df_quarantine.to_json(json_quarantine, orient="records", indent=2)
            exported_files["quarantine_csv"] = csv_quarantine
            exported_files["quarantine_json"] = json_quarantine

            # Export Manual Review Queue
            df_review = pd.read_sql_query(
                "SELECT * FROM manual_review_queue WHERE entity_type = ?", conn, params=(entity_type.value,)
            )
            csv_review = out_path / f"{entity_type.value.lower()}_review_queue.csv"
            json_review = out_path / f"{entity_type.value.lower()}_review_queue.json"
            df_review.to_csv(csv_review, index=False)
            df_review.to_json(json_review, orient="records", indent=2)
            exported_files["review_csv"] = csv_review
            exported_files["review_json"] = json_review

        return exported_files

    def get_master_count(self, entity_type: EntityType) -> int:
        table_name = "master_customers" if entity_type == EntityType.CUSTOMER else "master_products"
        with self._get_connection() as conn:
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
            return cursor.fetchone()[0]

    def get_lineage_count(self, entity_type: EntityType) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM record_lineage WHERE entity_type = ?", (entity_type.value,)
            )
            return cursor.fetchone()[0]

    def get_quarantine_count(self, entity_type: EntityType) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM quarantine_records WHERE entity_type = ?", (entity_type.value,)
            )
            return cursor.fetchone()[0]

