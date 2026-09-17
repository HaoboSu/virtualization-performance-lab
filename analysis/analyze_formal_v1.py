#!/usr/bin/env python3
"""Reproduce the completed Formal-v1 analysis from archived raw logs.

Run from repository root:
    python3 analysis/analyze_formal_v1.py
"""
from pathlib import Path
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
VM1_DIR = ROOT / "results" / "raw" / "formal_v1"
VM2_DIR = ROOT / "results" / "contention" / "formal_v1"
OUT = ROOT / "results" / "processed"
FIG = ROOT / "figures" / "formal_v1"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)
LOADS = [0, 25, 50, 75, 100]


def meta(text):
    out = {}
    for line in text.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def grab(text, pattern, cast=float):
    m = re.search(pattern, text, re.M)
    if not m:
        raise ValueError(f"missing pattern: {pattern}")
    return cast(m.group(1))


def stamp(value):
    return pd.to_datetime(value.replace(",", "."), utc=True)


def parse_vm1(path):
    text = path.read_text(errors="replace")
    m = meta(text)
    return {
        "vm1_file": path.name,
        "load_percent": int(m["configured_neighbor_load_percent"]),
        "run": int(m["run_number"]),
        "benchmark_duration_s": int(m["benchmark_duration_seconds"]),
        "benchmark_threads": int(m["benchmark_threads"]),
        "warmup_s": int(m["warmup_seconds"]),
        "vm1_hostname": m["hostname"],
        "vm1_clock_synchronized": m["clock_synchronized"],
        "repository_revision": m["repository_revision"],
        "vm1_warmup_started_at": stamp(m["warmup_started_at"]),
        "vm1_started_at": stamp(m["started_at"]),
        "vm1_finished_at": stamp(m["finished_at"]),
        "vm1_exit_status": int(m["exit_status"]),
        "events_per_sec": grab(text, r"events per second:\s+([0-9.]+)"),
        "total_events": grab(text, r"total number of events:\s+([0-9]+)", int),
        "latency_avg_ms": grab(text, r"^\s*avg:\s+([0-9.]+)"),
        "latency_max_ms": grab(text, r"^\s*max:\s+([0-9.]+)"),
        "latency_p95_ms": grab(text, r"95th percentile:\s+([0-9.]+)"),
    }


def parse_vm2(path):
    text = path.read_text(errors="replace")
    m = meta(text)
    failed = re.search(r"failed:\s*(\d+)", text)
    untrust = re.search(r"metrics untrustworthy:\s*(\d+)", text)
    return {
        "vm2_file": path.name,
        "load_percent": int(m["configured_load_percent"]),
        "run": int(m["run_number"]),
        "contention_duration_s": int(m["contention_duration_seconds"]),
        "vm2_cpu_workers": int(m["cpu_workers"]),
        "vm2_cpu_method": m["cpu_method"],
        "vm2_hostname": m["hostname"],
        "vm2_clock_synchronized": m["clock_synchronized"],
        "vm2_revision": m["repository_revision"],
        "vm2_started_at": stamp(m["started_at"]),
        "vm2_finished_at": stamp(m["finished_at"]),
        "vm2_exit_status": int(m["exit_status"]),
        "vm2_failed": int(failed.group(1)) if failed else np.nan,
        "vm2_metrics_untrustworthy": int(untrust.group(1)) if untrust else np.nan,
    }


def validate(vm1, vm2):
    if len(vm1) != 50 or len(vm2) != 40:
        raise ValueError(f"expected 50 VM1 and 40 VM2 logs; got {len(vm1)} and {len(vm2)}")
    expected1 = {(l, r) for l in LOADS for r in range(1, 11)}
    expected2 = {(l, r) for l in LOADS[1:] for r in range(1, 11)}
    if set(zip(vm1.load_percent, vm1.run)) != expected1:
        raise ValueError("VM1 load/run inventory does not match Formal-v1")
    if set(zip(vm2.load_percent, vm2.run)) != expected2:
        raise ValueError("VM2 load/run inventory does not match Formal-v1")
    if not (vm1.vm1_exit_status == 0).all() or not (vm2.vm2_exit_status == 0).all():
        raise ValueError("one or more runs did not exit successfully")
    if not (vm1.vm1_clock_synchronized == "yes").all() or not (vm2.vm2_clock_synchronized == "yes").all():
        raise ValueError("clock synchronization check failed")
    if not (vm2.vm2_cpu_method == "int64").all() or not (vm2.vm2_cpu_workers == 2).all():
        raise ValueError("unexpected VM2 contention configuration")


def holm(values):
    p = np.asarray(values, dtype=float)
    order = np.argsort(p)
    out = np.empty(len(p))
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, (len(p) - rank) * p[idx])
        out[idx] = min(running, 1.0)
    return out


def main():
    vm1 = pd.DataFrame(parse_vm1(p) for p in sorted(VM1_DIR.glob("*.txt")))
    vm2 = pd.DataFrame(parse_vm2(p) for p in sorted(VM2_DIR.glob("*.txt")))
    validate(vm1, vm2)
    df = vm1.merge(vm2, on=["load_percent", "run"], how="left")
    nonbase = df.load_percent > 0
    df["vm2_lead_before_benchmark_s"] = (df.vm1_started_at - df.vm2_started_at).dt.total_seconds()
    df["vm2_tail_after_benchmark_s"] = (df.vm2_finished_at - df.vm1_finished_at).dt.total_seconds()
    df["vm2_covers_benchmark"] = pd.Series(pd.NA, index=df.index, dtype="boolean")
    df.loc[nonbase, "vm2_covers_benchmark"] = (
        (df.loc[nonbase, "vm2_started_at"] <= df.loc[nonbase, "vm1_warmup_started_at"]) &
        (df.loc[nonbase, "vm2_finished_at"] >= df.loc[nonbase, "vm1_finished_at"])
    )
    if not df.loc[nonbase, "vm2_covers_benchmark"].all():
        raise ValueError("a VM2 load window does not cover its paired VM1 trial")

    baseline = df[df.load_percent == 0].set_index("run")
    df["paired_baseline_events_per_sec"] = df.run.map(baseline.events_per_sec)
    df["throughput_change_vs_paired_baseline_pct"] = (df.events_per_sec / df.paired_baseline_events_per_sec - 1) * 100
    df.loc[df.load_percent == 0, "throughput_change_vs_paired_baseline_pct"] = 0.0
    df["paired_baseline_p95_ms"] = df.run.map(baseline.latency_p95_ms)
    df["p95_change_vs_paired_baseline_pct"] = (df.latency_p95_ms / df.paired_baseline_p95_ms - 1) * 100
    df.loc[df.load_percent == 0, "p95_change_vs_paired_baseline_pct"] = 0.0
    df = df.sort_values(["load_percent", "run"])
    df.to_csv(OUT / "formal_v1_clean_runs.csv", index=False)

    result_cols = ["load_percent", "run", "events_per_sec", "total_events", "latency_avg_ms", "latency_max_ms", "latency_p95_ms", "vm1_exit_status", "vm1_started_at", "vm1_finished_at"]
    df[result_cols].to_csv(OUT / "formal_v1_results.csv", index=False)
    coverage_cols = ["load_percent", "run", "vm2_started_at", "vm1_warmup_started_at", "vm1_started_at", "vm1_finished_at", "vm2_finished_at", "vm2_lead_before_benchmark_s", "vm2_tail_after_benchmark_s", "vm2_covers_benchmark"]
    df.loc[nonbase, coverage_cols].to_csv(OUT / "formal_v1_coverage.csv", index=False)

    rows = []
    for load, g in df.groupby("load_percent"):
        eps, p95 = g.events_per_sec.astype(float), g.latency_p95_ms.astype(float)
        eps_ci = stats.t.interval(.95, len(eps)-1, loc=eps.mean(), scale=stats.sem(eps))
        p95_ci = stats.t.interval(.95, len(p95)-1, loc=p95.mean(), scale=stats.sem(p95))
        rows.append({
            "load_percent": load, "n": len(g),
            "events_per_sec_mean": eps.mean(), "events_per_sec_sd": eps.std(ddof=1),
            "events_per_sec_median": eps.median(), "events_per_sec_ci95_low": eps_ci[0], "events_per_sec_ci95_high": eps_ci[1],
            "events_per_sec_cv_pct": eps.std(ddof=1)/eps.mean()*100,
            "latency_avg_ms_mean": g.latency_avg_ms.mean(), "latency_p95_ms_mean": p95.mean(),
            "latency_p95_ms_sd": p95.std(ddof=1), "latency_p95_ms_ci95_low": p95_ci[0], "latency_p95_ms_ci95_high": p95_ci[1],
            "latency_max_ms_mean": g.latency_max_ms.mean(),
        })
    summary = pd.DataFrame(rows)
    b_eps = summary.loc[summary.load_percent == 0, "events_per_sec_mean"].iloc[0]
    b_p95 = summary.loc[summary.load_percent == 0, "latency_p95_ms_mean"].iloc[0]
    summary["throughput_change_vs_baseline_mean_pct"] = (summary.events_per_sec_mean / b_eps - 1) * 100
    summary["p95_change_vs_baseline_mean_pct"] = (summary.latency_p95_ms_mean / b_p95 - 1) * 100
    summary.to_csv(OUT / "formal_v1_summary.csv", index=False)

    test_rows = []
    for metric, label in [("events_per_sec", "throughput"), ("latency_p95_ms", "p95_latency")]:
        wide = df.pivot(index="run", columns="load_percent", values=metric)
        block = []
        for load in LOADS[1:]:
            diff = wide[load] - wide[0]
            tt = stats.ttest_rel(wide[load], wide[0])
            ww = stats.wilcoxon(wide[load], wide[0], method="auto")
            ci = stats.t.interval(.95, len(diff)-1, loc=diff.mean(), scale=stats.sem(diff))
            block.append({"metric": label, "load_percent": load, "mean_difference": diff.mean(), "ci95_low": ci[0], "ci95_high": ci[1], "paired_t_p": tt.pvalue, "wilcoxon_p": ww.pvalue, "cohen_dz": diff.mean()/diff.std(ddof=1)})
        ta, wa = holm([x["paired_t_p"] for x in block]), holm([x["wilcoxon_p"] for x in block])
        for i, row in enumerate(block):
            row["paired_t_holm_p"], row["wilcoxon_holm_p"] = ta[i], wa[i]
            test_rows.append(row)
    pd.DataFrame(test_rows).to_csv(OUT / "formal_v1_statistical_tests.csv", index=False)

    friedman = []
    for metric, label in [("events_per_sec", "throughput"), ("latency_avg_ms", "avg_latency"), ("latency_p95_ms", "p95_latency"), ("latency_max_ms", "max_latency")]:
        wide = df.pivot(index="run", columns="load_percent", values=metric)
        fr = stats.friedmanchisquare(*(wide[c].values for c in LOADS))
        friedman.append({"metric": label, "friedman_chi2": fr.statistic, "p_value": fr.pvalue})
    pd.DataFrame(friedman).to_csv(OUT / "formal_v1_friedman_tests.csv", index=False)

    flagged = []
    for load, g in df.groupby("load_percent"):
        q1, q3 = g.events_per_sec.quantile([.25, .75]); iqr = q3-q1; lo, hi = q1-1.5*iqr, q3+1.5*iqr
        for _, r in g[(g.events_per_sec < lo) | (g.events_per_sec > hi)].iterrows():
            flagged.append({"load_percent": int(load), "run": int(r.run), "events_per_sec": r.events_per_sec, "iqr_low": lo, "iqr_high": hi})
    outliers = pd.DataFrame(flagged)
    outliers.to_csv(OUT / "formal_v1_iqr_outliers.csv", index=False)
    flags = set(zip(outliers.load_percent, outliers.run)) if len(outliers) else set()
    df["throughput_iqr_outlier"] = [(int(l), int(r)) in flags for l, r in zip(df.load_percent, df.run)]
    sens = df[~df.throughput_iqr_outlier].copy()

    srows = []
    for label, data in [("primary_all_runs", df), ("sensitivity_exclude_iqr_outliers", sens)]:
        for load, g in data.groupby("load_percent"):
            srows.append({"analysis": label, "load_percent": int(load), "n": len(g), "throughput_mean": g.events_per_sec.mean(), "throughput_median": g.events_per_sec.median(), "throughput_sd": g.events_per_sec.std(ddof=1), "throughput_cv_pct": g.events_per_sec.std(ddof=1)/g.events_per_sec.mean()*100, "p95_mean_ms": g.latency_p95_ms.mean(), "p95_median_ms": g.latency_p95_ms.median()})
    ss = pd.DataFrame(srows)
    for label in ss.analysis.unique():
        base = ss[(ss.analysis == label) & (ss.load_percent == 0)].throughput_mean.iloc[0]
        mask = ss.analysis == label
        ss.loc[mask, "throughput_change_vs_baseline_mean_pct"] = (ss.loc[mask, "throughput_mean"]/base - 1)*100
    ss.to_csv(OUT / "formal_v1_sensitivity_summary.csv", index=False)

    stest = []
    for label, data in [("primary_all_runs", df), ("sensitivity_exclude_iqr_outliers", sens)]:
        for metric, mlabel in [("events_per_sec", "throughput"), ("latency_p95_ms", "p95_latency")]:
            wide = data.pivot(index="run", columns="load_percent", values=metric); block = []
            for load in LOADS[1:]:
                pair = wide[[0, load]].dropna(); diff = pair[load]-pair[0]
                tt = stats.ttest_rel(pair[load], pair[0]); ww = stats.wilcoxon(pair[load], pair[0], method="auto")
                ci = stats.t.interval(.95, len(diff)-1, loc=diff.mean(), scale=stats.sem(diff))
                block.append({"analysis": label, "metric": mlabel, "load_percent": load, "paired_n": len(pair), "mean_difference": diff.mean(), "ci95_low": ci[0], "ci95_high": ci[1], "cohen_dz": diff.mean()/diff.std(ddof=1), "paired_t_p": tt.pvalue, "wilcoxon_p": ww.pvalue})
            ta, wa = holm([x["paired_t_p"] for x in block]), holm([x["wilcoxon_p"] for x in block])
            for i, row in enumerate(block):
                row["paired_t_holm_p"], row["wilcoxon_holm_p"] = ta[i], wa[i]
                stest.append(row)
    pd.DataFrame(stest).to_csv(OUT / "formal_v1_sensitivity_tests.csv", index=False)

    slopes = []
    for run, g in df.groupby("run"):
        lr = stats.linregress(g.load_percent, g.events_per_sec)
        slopes.append({"run": int(run), "slope_events_per_sec_per_1pct_load": lr.slope, "slope_events_per_sec_per_25pct_load": lr.slope*25, "r_squared": lr.rvalue**2, "p_value_within_run": lr.pvalue})
    pd.DataFrame(slopes).to_csv(OUT / "formal_v1_run_level_slopes.csv", index=False)

    wide = df.pivot(index="run", columns="load_percent", values="events_per_sec")
    direction = []
    for a, b in [(0,25), (25,50), (50,75), (75,100), (0,100)]:
        diff = wide[b]-wide[a]
        direction.append({"comparison": f"{a}%->{b}%", "runs_lower_at_higher_load": int((diff<0).sum()), "runs_higher_at_higher_load": int((diff>0).sum()), "runs_equal": int((diff==0).sum()), "median_change_events_per_sec": diff.median(), "mean_change_events_per_sec": diff.mean()})
    pd.DataFrame(direction).to_csv(OUT / "formal_v1_direction_consistency.csv", index=False)

    ordered = summary.set_index("load_percent").loc[LOADS]; x = np.array(LOADS)
    fig, ax = plt.subplots(figsize=(8,5)); ax.errorbar(x, ordered.events_per_sec_mean, yerr=[ordered.events_per_sec_mean-ordered.events_per_sec_ci95_low, ordered.events_per_sec_ci95_high-ordered.events_per_sec_mean], marker="o", capsize=4); ax.set(xlabel="Configured neighbor CPU load (%)", ylabel="VM1 throughput (events/s)", title="Formal-v1 throughput under neighbor CPU contention"); ax.grid(True, alpha=.25); fig.tight_layout(); fig.savefig(FIG / "throughput_vs_contention.svg"); plt.close(fig)
    fig, ax = plt.subplots(figsize=(8,5)); ax.errorbar(x, ordered.latency_p95_ms_mean, yerr=[ordered.latency_p95_ms_mean-ordered.latency_p95_ms_ci95_low, ordered.latency_p95_ms_ci95_high-ordered.latency_p95_ms_mean], marker="o", capsize=4); ax.set(xlabel="Configured neighbor CPU load (%)", ylabel="VM1 P95 latency (ms)", title="Formal-v1 P95 latency under neighbor CPU contention"); ax.grid(True, alpha=.25); fig.tight_layout(); fig.savefig(FIG / "p95_latency_vs_contention.svg"); plt.close(fig)
    fig, ax = plt.subplots(figsize=(8,5));
    for label, g in ss.groupby("analysis"):
        g = g.sort_values("load_percent"); ax.plot(g.load_percent, g.throughput_mean, marker="o", label=label)
    ax.set(xlabel="Configured neighbor CPU load (%)", ylabel="Mean VM1 throughput (events/s)", title="Formal-v1 robustness to IQR outlier exclusion"); ax.legend(); ax.grid(True, alpha=.25); fig.tight_layout(); fig.savefig(FIG / "sensitivity_throughput.svg"); plt.close(fig)

    end = summary.loc[summary.load_percent == 100].iloc[0]
    print("Formal-v1 analysis complete.")
    print(f"VM1 logs: {len(vm1)}; VM2 logs: {len(vm2)}")
    print("All non-baseline VM2 windows cover their paired VM1 trials.")
    print(f"Baseline mean throughput: {b_eps:.2f} events/s")
    print(f"100% mean throughput: {end.events_per_sec_mean:.2f} events/s ({end.throughput_change_vs_baseline_mean_pct:.2f}% vs baseline)")


if __name__ == "__main__":
    main()
