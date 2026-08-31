#!/usr/bin/env python3
"""
Analyze sysbench CPU benchmark output files from virtualization-performance-lab.

Default repository layout:

virtualization-performance-lab/
├── analysis/
│   └── analyze_results.py
├── results/
│   ├── raw/
│   │   └── pilot_v2/
│   │       ├── baseline_run_1.txt
│   │       ├── medium_50_run_1.txt
│   │       └── heavy_100_run_1.txt
│   └── processed/
└── figures/

The script:
1. Parses raw sysbench .txt files without modifying them.
2. Creates a per-run CSV.
3. Creates a summary CSV with mean, sample SD and CV.
4. Calculates changes relative to baseline.
5. Creates three figures if matplotlib is installed.

Supported filename patterns include:
- baseline_run_1.txt
- light_25_run_1.txt
- contention_25_run_1.txt
- medium_50_run_1.txt
- contention_50_run_1.txt
- high_75_run_1.txt
- contention_75_run_1.txt
- heavy_100_run_1.txt
- contention_100_run_1.txt

Usage from the repository root:
    python3 analysis/analyze_results.py

Optional:
    python3 analysis/analyze_results.py --raw-dir results/raw/pilot_v2
    python3 analysis/analyze_results.py --raw-dir /path/to/files --output-root /path/to/output
"""

from __future__ import annotations

import argparse
import csv
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional


def parse_args() -> argparse.Namespace:
    script_path = Path(__file__).resolve()
    default_repo_root = script_path.parents[1] if len(script_path.parents) >= 2 else Path.cwd()

    parser = argparse.ArgumentParser(
        description="Parse and summarize sysbench CPU benchmark result files."
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("/home/haobo/virtualization-performance-lab/results/raw/pilot_v2/"),
        help="Directory containing raw sysbench .txt files.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=default_repo_root,
        help="Repository/output root containing results/processed and figures.",
    )
    return parser.parse_args()


def extract_float(text: str, pattern: str, field_name: str) -> float:
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        raise ValueError(f"Could not find '{field_name}'")
    return float(match.group(1))


def extract_int(text: str, pattern: str, field_name: str) -> int:
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        raise ValueError(f"Could not find '{field_name}'")
    return int(match.group(1))


def detect_condition(filename: str) -> tuple[int, str]:
    lower = filename.lower()

    if "baseline" in lower:
        return 0, "Baseline"

    pressure_match = re.search(r"(?:_|^)(25|50|75|100)(?:_|%)", lower)
    if pressure_match:
        pressure = int(pressure_match.group(1))
        return pressure, f"{pressure}% pressure"

    # Fallbacks for descriptive names without explicit numeric pressure.
    if "light" in lower:
        return 25, "25% pressure"
    if "medium" in lower:
        return 50, "50% pressure"
    if "high" in lower:
        return 75, "75% pressure"
    if "heavy" in lower:
        return 100, "100% pressure"

    raise ValueError(
        "Unable to determine contention level from filename. "
        "Use a name containing baseline, 25, 50, 75 or 100."
    )


def detect_run_number(filename: str) -> int:
    match = re.search(r"_run_(\d+)", filename.lower())
    if not match:
        raise ValueError("Unable to determine run number from filename.")
    return int(match.group(1))


def parse_sysbench_file(path: Path) -> Dict[str, object]:
    text = path.read_text(encoding="utf-8", errors="replace")

    pressure, condition = detect_condition(path.name)
    run_number = detect_run_number(path.name)

    result: Dict[str, object] = {
        "file": path.name,
        "pressure_percent": pressure,
        "condition": condition,
        "run": run_number,
        "events_per_second": extract_float(
            text, r"events per second:\s*([0-9.]+)", "events per second"
        ),
        "total_time_s": extract_float(
            text, r"total time:\s*([0-9.]+)s", "total time"
        ),
        "total_events": extract_int(
            text, r"total number of events:\s*(\d+)", "total number of events"
        ),
        "latency_min_ms": extract_float(
            text, r"^\s*min:\s*([0-9.]+)", "minimum latency"
        ),
        "latency_avg_ms": extract_float(
            text, r"^\s*avg:\s*([0-9.]+)", "average latency"
        ),
        "latency_max_ms": extract_float(
            text, r"^\s*max:\s*([0-9.]+)", "maximum latency"
        ),
        "latency_p95_ms": extract_float(
            text, r"^\s*95th percentile:\s*([0-9.]+)", "95th percentile latency"
        ),
    }
    return result


def mean(values: List[float]) -> float:
    return statistics.mean(values)


def median(values: List[float]) -> float:
    return statistics.median(values)


def sample_sd(values: List[float]) -> float:
    return statistics.stdev(values) if len(values) > 1 else 0.0


def cv_percent(values: List[float]) -> float:
    m = mean(values)
    return (sample_sd(values) / m * 100.0) if m else 0.0


def percent_degradation(baseline: float, value: float) -> float:
    """Positive means worse throughput relative to baseline."""
    return ((baseline - value) / baseline * 100.0) if baseline else 0.0


def percent_increase(baseline: float, value: float) -> float:
    """Positive means latency increased relative to baseline."""
    return ((value - baseline) / baseline * 100.0) if baseline else 0.0


def write_per_run_csv(rows: List[Dict[str, object]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "file",
        "pressure_percent",
        "condition",
        "run",
        "events_per_second",
        "total_time_s",
        "total_events",
        "latency_min_ms",
        "latency_avg_ms",
        "latency_max_ms",
        "latency_p95_ms",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def summarize(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    grouped: Dict[int, List[Dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[int(row["pressure_percent"])].append(row)

    if 0 not in grouped:
        raise ValueError("No baseline files were found; cannot calculate relative changes.")

    for group in grouped.values():
        group.sort(key=lambda item: int(item["run"]))

    baseline_throughput = mean(
        [float(r["events_per_second"]) for r in grouped[0]]
    )
    baseline_avg_latency = mean(
        [float(r["latency_avg_ms"]) for r in grouped[0]]
    )
    baseline_p95 = mean(
        [float(r["latency_p95_ms"]) for r in grouped[0]]
    )

    summaries: List[Dict[str, object]] = []

    for pressure in sorted(grouped):
        group = grouped[pressure]
        throughput = [float(r["events_per_second"]) for r in group]
        avg_latency = [float(r["latency_avg_ms"]) for r in group]
        p95 = [float(r["latency_p95_ms"]) for r in group]
        max_latency = [float(r["latency_max_ms"]) for r in group]

        summaries.append(
            {
                "pressure_percent": pressure,
                "condition": group[0]["condition"],
                "n": len(group),

                "throughput_mean_events_s": mean(throughput),
                "throughput_median_events_s": median(throughput),
                "throughput_sd_events_s": sample_sd(throughput),
                "throughput_cv_percent": cv_percent(throughput),
                "throughput_degradation_vs_baseline_percent":
                    percent_degradation(baseline_throughput, mean(throughput)),

                "avg_latency_mean_ms": mean(avg_latency),
                "avg_latency_median_ms": median(avg_latency),
                "avg_latency_sd_ms": sample_sd(avg_latency),
                "avg_latency_cv_percent": cv_percent(avg_latency),
                "avg_latency_increase_vs_baseline_percent":
                    percent_increase(baseline_avg_latency, mean(avg_latency)),

                "p95_latency_mean_ms": mean(p95),
                "p95_latency_median_ms": median(p95),
                "p95_latency_sd_ms": sample_sd(p95),
                "p95_latency_cv_percent": cv_percent(p95),
                "p95_latency_increase_vs_baseline_percent":
                    percent_increase(baseline_p95, mean(p95)),

                "max_latency_mean_ms": mean(max_latency),
                "max_latency_median_ms": median(max_latency),
            }
        )

    return summaries


def write_summary_csv(rows: List[Dict[str, object]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fields = [
        "pressure_percent",
        "condition",
        "n",
        "throughput_mean_events_s",
        "throughput_median_events_s",
        "throughput_sd_events_s",
        "throughput_cv_percent",
        "throughput_degradation_vs_baseline_percent",
        "avg_latency_mean_ms",
        "avg_latency_median_ms",
        "avg_latency_sd_ms",
        "avg_latency_cv_percent",
        "avg_latency_increase_vs_baseline_percent",
        "p95_latency_mean_ms",
        "p95_latency_median_ms",
        "p95_latency_sd_ms",
        "p95_latency_cv_percent",
        "p95_latency_increase_vs_baseline_percent",
        "max_latency_mean_ms",
        "max_latency_median_ms",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def print_summary(summary_rows: List[Dict[str, object]]) -> None:
    print("\nSummary")
    print("=" * 96)
    print(
        f"{'Pressure':>9}  {'N':>3}  {'Throughput mean ± SD':>27}  "
        f"{'CV%':>7}  {'ΔThroughput%':>13}  {'Avg lat ms':>10}  "
        f"{'P95 ms':>8}  {'ΔP95%':>8}"
    )
    print("-" * 96)

    for row in summary_rows:
        print(
            f"{int(row['pressure_percent']):>8}%  "
            f"{int(row['n']):>3}  "
            f"{float(row['throughput_mean_events_s']):>10.2f} ± "
            f"{float(row['throughput_sd_events_s']):<8.2f}  "
            f"{float(row['throughput_cv_percent']):>6.2f}  "
            f"{float(row['throughput_degradation_vs_baseline_percent']):>12.2f}  "
            f"{float(row['avg_latency_mean_ms']):>10.3f}  "
            f"{float(row['p95_latency_mean_ms']):>8.3f}  "
            f"{float(row['p95_latency_increase_vs_baseline_percent']):>7.2f}"
        )


def make_figures(summary_rows: List[Dict[str, object]], figures_dir: Path) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print(
            "\nmatplotlib is not installed, so CSV files were created but figures were skipped."
        )
        print("Install it with: python3 -m pip install matplotlib")
        return

    figures_dir.mkdir(parents=True, exist_ok=True)

    pressures = [int(row["pressure_percent"]) for row in summary_rows]

    throughput_means = [
        float(row["throughput_mean_events_s"]) for row in summary_rows
    ]
    throughput_sds = [
        float(row["throughput_sd_events_s"]) for row in summary_rows
    ]

    plt.figure(figsize=(7, 4.5))
    plt.errorbar(
        pressures,
        throughput_means,
        yerr=throughput_sds,
        marker="o",
        capsize=4,
    )
    plt.xlabel("CPU pressure generated by neighboring VM (%)")
    plt.ylabel("Throughput (events/s)")
    plt.title("Sysbench CPU Throughput vs Neighboring-VM CPU Pressure")
    plt.xticks(pressures)
    plt.grid(True, alpha=0.25)
    plt.tight_layout()
    plt.savefig(figures_dir / "throughput_vs_pressure.png", dpi=180)
    plt.close()

    avg_latency_means = [
        float(row["avg_latency_mean_ms"]) for row in summary_rows
    ]
    avg_latency_sds = [
        float(row["avg_latency_sd_ms"]) for row in summary_rows
    ]

    plt.figure(figsize=(7, 4.5))
    plt.errorbar(
        pressures,
        avg_latency_means,
        yerr=avg_latency_sds,
        marker="o",
        capsize=4,
    )
    plt.xlabel("CPU pressure generated by neighboring VM (%)")
    plt.ylabel("Average latency (ms)")
    plt.title("Average Latency vs Neighboring-VM CPU Pressure")
    plt.xticks(pressures)
    plt.grid(True, alpha=0.25)
    plt.tight_layout()
    plt.savefig(figures_dir / "avg_latency_vs_pressure.png", dpi=180)
    plt.close()

    p95_means = [
        float(row["p95_latency_mean_ms"]) for row in summary_rows
    ]
    p95_sds = [
        float(row["p95_latency_sd_ms"]) for row in summary_rows
    ]

    plt.figure(figsize=(7, 4.5))
    plt.errorbar(
        pressures,
        p95_means,
        yerr=p95_sds,
        marker="o",
        capsize=4,
    )
    plt.xlabel("CPU pressure generated by neighboring VM (%)")
    plt.ylabel("95th-percentile latency (ms)")
    plt.title("P95 Latency vs Neighboring-VM CPU Pressure")
    plt.xticks(pressures)
    plt.grid(True, alpha=0.25)
    plt.tight_layout()
    plt.savefig(figures_dir / "p95_latency_vs_pressure.png", dpi=180)
    plt.close()

    print(f"Figures written to: {figures_dir}")


def main() -> int:
    args = parse_args()
    raw_dir = args.raw_dir.expanduser().resolve()
    output_root = args.output_root.expanduser().resolve()

    if not raw_dir.exists():
        print(f"ERROR: raw data directory does not exist: {raw_dir}", file=sys.stderr)
        return 1

    files = sorted(raw_dir.glob("*.txt"))
    if not files:
        print(f"ERROR: no .txt files found in: {raw_dir}", file=sys.stderr)
        return 1

    rows: List[Dict[str, object]] = []
    errors: List[str] = []

    for path in files:
        try:
            rows.append(parse_sysbench_file(path))
        except ValueError as exc:
            errors.append(f"{path.name}: {exc}")

    if errors:
        print("Skipped files that could not be parsed:")
        for error in errors:
            print(f"  - {error}")

    if not rows:
        print("ERROR: no valid sysbench result files were parsed.", file=sys.stderr)
        return 1

    rows.sort(key=lambda row: (int(row["pressure_percent"]), int(row["run"])))

    processed_dir = output_root / "results" / "processed"
    figures_dir = output_root / "figures"

    per_run_csv = processed_dir / "pilot_v2_results.csv"
    summary_csv = processed_dir / "pilot_v2_summary.csv"

    write_per_run_csv(rows, per_run_csv)
    summary_rows = summarize(rows)
    write_summary_csv(summary_rows, summary_csv)

    print(f"Parsed {len(rows)} result files from: {raw_dir}")
    print(f"Per-run CSV written to: {per_run_csv}")
    print(f"Summary CSV written to: {summary_csv}")

    print_summary(summary_rows)
    make_figures(summary_rows, figures_dir)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

