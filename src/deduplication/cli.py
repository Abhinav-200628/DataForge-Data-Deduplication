"""
Command-line interface for the deduplication pipeline using argparse.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

from deduplication.generator.synthetic_data import (
    generate_customer_dataset,
    generate_product_dataset,
)
from deduplication.orchestration import DeduplicationPipeline
from deduplication.reporting.validation_report import ReportGenerator
from deduplication.schemas.common import EntityType
from deduplication.storage.repository import SQLiteRepository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="deduplication",
        description="Production-minded customer and product record deduplication pipeline.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. 'run' command
    run_parser = subparsers.add_parser("run", help="Run deduplication pipeline on an input CSV.")
    run_parser.add_argument(
        "--entity",
        choices=["customer", "product"],
        required=True,
        help="Entity domain to deduplicate.",
    )
    run_parser.add_argument("--input", required=True, type=Path, help="Path to input CSV file.")
    run_parser.add_argument(
        "--db", default=Path("pipeline.db"), type=Path, help="Path to SQLite database file."
    )
    run_parser.add_argument(
        "--output-dir", default=Path("output"), type=Path, help="Directory to export CSV and JSON outputs."
    )
    run_parser.add_argument(
        "--config", type=Path, default=None, help="Optional JSON configuration path."
    )

    # 2. 'generate-data' command
    gen_parser = subparsers.add_parser("generate-data", help="Generate synthetic test datasets.")
    gen_parser.add_argument(
        "--entity", choices=["customer", "product"], default="customer", help="Entity type to generate."
    )
    gen_parser.add_argument("--count", type=int, default=1000, help="Number of records to generate.")
    gen_parser.add_argument("--seed", type=int, default=42, help="Fixed random seed for reproducibility.")
    gen_parser.add_argument(
        "--dupe-rate", type=float, default=0.20, help="Fraction of duplicate records."
    )
    gen_parser.add_argument(
        "--error-rate", type=float, default=0.05, help="Fraction of invalid/malformed records."
    )
    gen_parser.add_argument(
        "--output-dir", type=Path, default=Path("data/sample"), help="Output directory for CSV and ground truth."
    )

    # 3. 'benchmark' command
    bench_parser = subparsers.add_parser("benchmark", help="Run scale performance benchmark.")
    bench_parser.add_argument(
        "--entity", choices=["customer", "product"], default="customer", help="Entity type to benchmark."
    )
    bench_parser.add_argument(
        "--count", type=int, default=10000, help="Number of records to benchmark (e.g. 10000 or 100000)."
    )
    bench_parser.add_argument(
        "--db", default=Path("benchmark.db"), type=Path, help="Benchmark SQLite database path."
    )
    bench_parser.add_argument(
        "--output-dir", default=Path("benchmark_output"), type=Path, help="Output directory."
    )

    # 4. 'report' command
    report_parser = subparsers.add_parser("report", help="Generate validation & reconciliation report.")
    report_parser.add_argument(
        "--run-id",
        default="latest",
        help="Pipeline Run ID to inspect (default: 'latest' for the most recent run).",
    )
    report_parser.add_argument(
        "--db", default=Path("pipeline.db"), type=Path, help="Path to SQLite database."
    )
    report_parser.add_argument(
        "--ground-truth", type=Path, default=None, help="Optional path to ground truth JSON clusters."
    )
    report_parser.add_argument(
        "--format", choices=["markdown", "json"], default="markdown", help="Report output format."
    )

    # 5. 'review' command
    review_parser = subparsers.add_parser("review", help="Inspect and triage manual review queue.")
    review_parser.add_argument(
        "--db", default=Path("pipeline.db"), type=Path, help="Path to SQLite database."
    )
    review_parser.add_argument("--list", action="store_true", help="List pending review items.")
    review_parser.add_argument("--limit", type=int, default=10, help="Max items to display.")

    return parser


def handle_run(args: argparse.Namespace) -> int:
    entity = EntityType.CUSTOMER if args.entity.lower() == "customer" else EntityType.PRODUCT
    config = {}
    if args.config and args.config.exists():
        with open(args.config, "r", encoding="utf-8") as f:
            config = json.load(f)

    pipeline = DeduplicationPipeline(
        entity_type=entity,
        db_path=args.db,
        output_dir=args.output_dir,
        config=config,
    )

    print(f"[*] Starting {entity.value} Deduplication Pipeline...")
    print(f"[*] Input File: {args.input}")
    print(f"[*] Database: {args.db}")
    print(f"[*] Output Dir: {args.output_dir}")

    metrics = pipeline.run(input_path=args.input)

    print("\n[+] Run Completed Successfully!")
    print(f"    Run ID:               {metrics.run_id}")
    print(f"    Status:               {metrics.status.value}")
    print(f"    Elapsed Time:         {metrics.elapsed_seconds:.3f}s")
    print(f"    Total Input Rows:     {metrics.input_count}")
    print(f"    Valid Rows:           {metrics.valid_count}")
    print(f"    Quarantined Rows:     {metrics.quarantined_count}")
    print(f"    Exact Merges:         {metrics.exact_matches}")
    print(f"    Probable Merges:      {metrics.probable_matches}")
    print(f"    Manual Reviews:       {metrics.manual_reviews}")
    print(f"    Distinct Records:     {metrics.distinct_count}")
    print(f"    Master Entities:      {metrics.master_records_created}")
    return 0


def handle_generate_data(args: argparse.Namespace) -> int:
    print(f"[*] Generating {args.count} synthetic {args.entity} records (seed={args.seed})...")
    if args.entity.lower() == "customer":
        records, gt = generate_customer_dataset(
            count=args.count,
            seed=args.seed,
            duplicate_rate=args.dupe_rate,
            error_rate=args.error_rate,
            output_dir=args.output_dir,
        )
    else:
        records, gt = generate_product_dataset(
            count=args.count,
            seed=args.seed,
            duplicate_rate=args.dupe_rate,
            error_rate=args.error_rate,
            output_dir=args.output_dir,
        )

    print(f"[+] Successfully generated {len(records)} records in '{args.output_dir}'")
    print(f"    Expected duplicate clusters in ground truth: {len(gt)}")
    return 0


def handle_benchmark(args: argparse.Namespace) -> int:
    bench_dir = args.output_dir / "bench_data"
    bench_dir.mkdir(parents=True, exist_ok=True)
    entity = EntityType.CUSTOMER if args.entity.lower() == "customer" else EntityType.PRODUCT

    entity_plural = f"{args.entity.lower()}s"
    csv_path = bench_dir / f"{entity_plural}_{args.count}.csv"
    gt_path = bench_dir / f"{entity_plural}_{args.count}_ground_truth.json"

    print(f"[*] Preparing benchmark dataset: {args.count} {args.entity} records...")
    gen_start = time.perf_counter()
    if args.entity.lower() == "customer":
        generate_customer_dataset(count=args.count, seed=42, output_dir=bench_dir)
    else:
        generate_product_dataset(count=args.count, seed=42, output_dir=bench_dir)
    gen_time = time.perf_counter() - gen_start
    print(f"[+] Dataset generation took {gen_time:.2f}s")

    import os
    import platform
    import tracemalloc

    print("\n[*] Executing Benchmark Pipeline...")
    tracemalloc.start()
    pipeline = DeduplicationPipeline(
        entity_type=entity,
        db_path=args.db,
        output_dir=args.output_dir,
    )
    bench_start = time.perf_counter()
    metrics = pipeline.run(input_path=csv_path)
    total_bench_time = time.perf_counter() - bench_start
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_mb = peak_bytes / (1024 * 1024)

    throughput = metrics.input_count / metrics.elapsed_seconds if metrics.elapsed_seconds > 0 else 0.0

    print("\n" + "=" * 60)
    print("           BENCHMARK PERFORMANCE SUMMARY")
    print("=" * 60)
    print(f"Machine OS:            {platform.platform()}")
    print(f"CPU Cores:             {os.cpu_count()}")
    print(f"Python Version:        {platform.python_version()}")
    print(f"Entity Domain:         {entity.value}")
    print(f"Total Input Records:   {metrics.input_count}")
    print(f"Valid Records:         {metrics.valid_count}")
    print(f"Pipeline Elapsed Time: {metrics.elapsed_seconds:.3f}s")
    print(f"Peak Memory (Traced):  {peak_mb:.2f} MB")
    print(f"Overall Throughput:    {throughput:,.1f} records/second")
    print(f"Golden Masters:        {metrics.master_records_created}")
    print(f"Quarantined Records:   {metrics.quarantined_count}")
    print("=" * 60)

    # Generate accuracy report against ground truth
    reporter = ReportGenerator(db_path=args.db)
    report_data = reporter.generate_run_report(metrics.run_id, ground_truth_path=gt_path)
    report_data["benchmark_hardware"] = {
        "os": platform.platform(),
        "cpu_count": os.cpu_count(),
        "python_version": platform.python_version(),
        "peak_memory_mb": round(peak_mb, 2),
        "throughput_records_per_sec": round(throughput, 1),
    }
    md_report = reporter.format_markdown_report(report_data)
    # Append hardware & memory section to report
    hardware_section = (
        f"\n## 5. Benchmark Hardware & Resource Profile\n\n"
        f"- **Operating System**: `{platform.platform()}`\n"
        f"- **CPU Count**: `{os.cpu_count()} logical cores`\n"
        f"- **Python Runtime**: `{platform.python_version()}`\n"
        f"- **Peak Traced Memory**: `{peak_mb:.2f} MB`\n"
        f"- **Throughput**: `{throughput:,.1f} records/second`\n"
    )
    md_report += hardware_section
    report_file = args.output_dir / "benchmark_report.md"
    report_file.write_text(md_report, encoding="utf-8")
    print(f"[+] Benchmark report saved to: {report_file}")
    return 0


def handle_report(args: argparse.Namespace) -> int:
    run_id = args.run_id
    if not run_id or run_id.lower() in ("latest", "last", "auto"):
        repo = SQLiteRepository(args.db)
        with repo._get_connection() as conn:
            row = conn.execute(
                "SELECT run_id FROM pipeline_runs ORDER BY started_at DESC LIMIT 1"
            ).fetchone()
            if not row:
                print(f"[!] No pipeline runs found in database '{args.db}'. Run the pipeline first.")
                return 1
            run_id = row[0]
            print(f"[*] Auto-selected latest run: {run_id}\n")

    reporter = ReportGenerator(db_path=args.db)
    report_data = reporter.generate_run_report(run_id, ground_truth_path=args.ground_truth)
    if args.format == "json":
        print(json.dumps(report_data, indent=2))
    else:
        print(reporter.format_markdown_report(report_data))
    return 0


def handle_review(args: argparse.Namespace) -> int:
    repo = SQLiteRepository(args.db)
    with repo._get_connection() as conn:
        cursor = conn.execute(
            "SELECT review_id, entity_type, source_system, source_record_id, similarity_score, reasons, status "
            "FROM manual_review_queue WHERE status = 'PENDING' LIMIT ?",
            (args.limit,),
        )
        rows = cursor.fetchall()
        print(f"\n[*] Manual Review Queue (Pending Items, Limit {args.limit}):")
        if not rows:
            print("    No pending items requiring manual review.")
            return 0

        for r in rows:
            print(f"  - [{r['review_id']}] {r['entity_type']} ({r['source_system']}:{r['source_record_id']}) "
                  f"Score: {r['similarity_score']:.2f} | Reason: {r['reasons']}")
    return 0


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run":
        sys.exit(handle_run(args))
    elif args.command == "generate-data":
        sys.exit(handle_generate_data(args))
    elif args.command == "benchmark":
        sys.exit(handle_benchmark(args))
    elif args.command == "report":
        sys.exit(handle_report(args))
    elif args.command == "review":
        sys.exit(handle_review(args))


if __name__ == "__main__":
    main()

