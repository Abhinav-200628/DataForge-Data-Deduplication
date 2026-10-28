"""
Validation, data-quality, and benchmark reporting engine.

Generates comprehensive markdown and json reports, including data quality health,
reconciliation balance checks, and ground-truth precision/recall evaluations.
"""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from typing import Any, Optional, Union

from deduplication.schemas.common import EntityType


class ReportGenerator:
    """Generates analytical and operational reports for pipeline runs."""

    def __init__(self, db_path: Union[str, Path] = "pipeline.db") -> None:
        self.db_path = Path(db_path)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def generate_run_report(
        self,
        run_id: str,
        ground_truth_path: Optional[Union[str, Path]] = None,
    ) -> dict[str, Any]:
        """
        Extract detailed operational metrics for a run and evaluate ground truth if provided.
        """
        with self._get_connection() as conn:
            # 1. Fetch run info
            cursor = conn.execute("SELECT * FROM pipeline_runs WHERE run_id = ?", (run_id,))
            run_row = cursor.fetchone()
            if not run_row:
                raise ValueError(f"Run ID '{run_id}' not found in database.")

            run_dict = dict(run_row)
            entity_type = run_dict["entity_type"]

            # 2. Fetch quarantine breakdown
            q_cursor = conn.execute(
                "SELECT rejection_reasons FROM quarantine_records WHERE run_id = ?", (run_id,)
            )
            q_rows = q_cursor.fetchall()
            rejection_counts: dict[str, int] = {}
            for r in q_rows:
                reasons_list = json.loads(r[0])
                for detail in reasons_list:
                    code = detail.get("code", "UNKNOWN")
                    rejection_counts[code] = rejection_counts.get(code, 0) + 1

            # 3. Fetch lineage decisions
            lin_cursor = conn.execute(
                "SELECT decision, match_rule_id, COUNT(*) FROM record_lineage "
                "WHERE run_id = ? GROUP BY decision, match_rule_id",
                (run_id,),
            )
            rule_counts = [
                {"decision": row[0], "rule_id": row[1], "count": row[2]}
                for row in lin_cursor.fetchall()
            ]

            # 4. Fetch Master Record Count
            table_name = "master_customers" if entity_type == EntityType.CUSTOMER.value else "master_products"
            m_cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
            total_masters = m_cursor.fetchone()[0]

            # 5. Deduplication Efficiency Ratio
            valid_count = run_dict.get("valid_count", 0)
            dedup_ratio = (
                (1.0 - (total_masters / valid_count)) * 100.0 if valid_count > 0 else 0.0
            )

            # 6. Reconciliation Assertions
            in_count = run_dict.get("input_count", 0)
            q_count = run_dict.get("quarantined_count", 0)
            reconciled = in_count == (valid_count + q_count)

            report_data: dict[str, Any] = {
                "run_info": run_dict,
                "reconciliation": {
                    "input_count": in_count,
                    "valid_count": valid_count,
                    "quarantined_count": q_count,
                    "is_balanced": reconciled,
                    "formula": f"{in_count} == {valid_count} + {q_count}",
                },
                "deduplication_metrics": {
                    "total_valid_records": valid_count,
                    "golden_master_records": total_masters,
                    "deduplication_ratio_pct": round(dedup_ratio, 2),
                    "rule_breakdown": rule_counts,
                },
                "data_quality_quarantine": {
                    "total_quarantined": q_count,
                    "error_breakdown": rejection_counts,
                },
            }

            # 7. Evaluate Ground Truth if provided
            if ground_truth_path:
                gt_path = Path(ground_truth_path)
                if gt_path.exists():
                    evaluation = self._evaluate_ground_truth(conn, run_id, gt_path)
                    report_data["ground_truth_evaluation"] = evaluation

            return report_data

    def _evaluate_ground_truth(
        self, conn: sqlite3.Connection, run_id: str, gt_path: Path
    ) -> dict[str, Any]:
        """
        Compare pipeline clusters against known ground truth clusters using pairwise Precision & Recall.
        """
        with open(gt_path, "r", encoding="utf-8") as f:
            expected_clusters: dict[str, list[str]] = json.load(f)

        # Build expected pairwise links
        expected_pairs: set[tuple[str, str]] = set()
        for members in expected_clusters.values():
            if len(members) > 1:
                sorted_members = sorted(members)
                for i in range(len(sorted_members)):
                    for j in range(i + 1, len(sorted_members)):
                        expected_pairs.add((sorted_members[i], sorted_members[j]))

        # Build predicted pairwise links from lineage (records sharing the same master_id)
        cursor = conn.execute(
            "SELECT source_record_id, master_id FROM record_lineage WHERE run_id = ?",
            (run_id,),
        )
        predicted_clusters: dict[str, list[str]] = {}
        for src_id, master_id in cursor.fetchall():
            predicted_clusters.setdefault(master_id, []).append(src_id)

        predicted_pairs: set[tuple[str, str]] = set()
        for members in predicted_clusters.values():
            if len(members) > 1:
                sorted_members = sorted(members)
                for i in range(len(sorted_members)):
                    for j in range(i + 1, len(sorted_members)):
                        predicted_pairs.add((sorted_members[i], sorted_members[j]))

        true_positives = len(expected_pairs & predicted_pairs)
        false_positives = len(predicted_pairs - expected_pairs)
        false_negatives = len(expected_pairs - predicted_pairs)

        precision = (
            true_positives / (true_positives + false_positives)
            if (true_positives + false_positives) > 0
            else 1.0
        )
        recall = (
            true_positives / (true_positives + false_negatives)
            if (true_positives + false_negatives) > 0
            else 1.0
        )
        f1 = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        return {
            "expected_duplicate_pairs": len(expected_pairs),
            "predicted_duplicate_pairs": len(predicted_pairs),
            "true_positives": true_positives,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
        }

    def format_markdown_report(self, report_data: dict[str, Any]) -> str:
        """Render report as a clean GitHub-flavored markdown document."""
        r_info = report_data["run_info"]
        recon = report_data["reconciliation"]
        dedup = report_data["deduplication_metrics"]
        dq = report_data["data_quality_quarantine"]

        lines = [
            f"# Operational & Reconciliation Validation Report: `{r_info['run_id']}`",
            "",
            f"- **Entity Type**: `{r_info['entity_type']}`",
            f"- **Execution Status**: `{r_info['status']}`",
            f"- **Elapsed Time**: `{r_info['elapsed_seconds']}s`",
            f"- **Run Timestamp**: `{r_info['started_at']}`",
            "",
            "## 1. Reconciliation Conservation Check",
            "",
            "| Metric | Count | Status |",
            "| :--- | :--- | :--- |",
            f"| Total Input Records | `{recon['input_count']}` | — |",
            f"| Valid Processed Records | `{recon['valid_count']}` | — |",
            f"| Quarantined Records | `{recon['quarantined_count']}` | — |",
            f"| **Conservation Balance** (`In == Valid + Quarantine`) | `{recon['formula']}` | **{'PASSED' if recon['is_balanced'] else 'FAILED'}** |",
            "",
            "## 2. Deduplication & Consolidation Metrics",
            "",
            f"- **Golden Master Records Generated**: `{dedup['golden_master_records']}`",
            f"- **Deduplication Ratio**: `{dedup['deduplication_ratio_pct']}%`",
            "",
            "### Rule Attribution Breakdown",
            "",
            "| Decision | Match Rule ID | Records Attributed |",
            "| :--- | :--- | :--- |",
        ]

        for rule in dedup["rule_breakdown"]:
            lines.append(f"| `{rule['decision']}` | `{rule['rule_id']}` | `{rule['count']}` |")

        lines.extend([
            "",
            "## 3. Data Quality & Quarantine Distribution",
            "",
            f"- **Total Quarantined**: `{dq['total_quarantined']}`",
            "",
            "| Rejection Code | Occurrences |",
            "| :--- | :--- |",
        ])

        for code, cnt in dq["error_breakdown"].items():
            lines.append(f"| `{code}` | `{cnt}` |")

        if "ground_truth_evaluation" in report_data:
            gt = report_data["ground_truth_evaluation"]
            lines.extend([
                "",
                "## 4. Ground-Truth Accuracy Evaluation",
                "",
                "| Metric | Value |",
                "| :--- | :--- |",
                f"| True Positives (Correct Merges) | `{gt['true_positives']}` |",
                f"| False Positives (Over-merges) | `{gt['false_positives']}` |",
                f"| False Negatives (Missed Merges) | `{gt['false_negatives']}` |",
                f"| **Pairwise Precision** | **`{gt['precision'] * 100:.2f}%`** |",
                f"| **Pairwise Recall** | **`{gt['recall'] * 100:.2f}%`** |",
                f"| **F1 Score** | **`{gt['f1_score']:.4f}`** |",
            ])

        return "\n".join(lines)
